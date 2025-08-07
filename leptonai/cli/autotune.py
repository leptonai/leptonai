import click
import sys
import re
import logging
from rich.console import Console
from .util import click_group
from nemo.collections.llm.tools.autotuner.args import AutoTuneArgs
from nemo.collections.llm.tools.autotuner.core.predictive_config_builder import list_models as list_models_impl

# Import data launcher functions
import sys
import os

from nemo.collections.llm.tools.autotuner.launcher import (
    launch_generate_remote,
    launch_run_remote,
    launch_results_remote,
    launch_list_configs_remote
)

logger = logging.getLogger(__name__)

console = Console()

# --- Validation Functions ---
def validate_positive_int(ctx, param, value):
    if value is None:
        return value
    if value <= 0:
        raise click.BadParameter(f"{param.name} must be a positive integer, got: {value}")
    return value

def validate_positive_float(ctx, param, value):
    if value is None:
        return value
    if value <= 0:
        raise click.BadParameter(f"{param.name} must be a positive number, got: {value}")
    return value

def validate_model_callback(ctx, param, value):
    if value is None:
        return value
    # Minimal check: model name must be non-empty string
    if not isinstance(value, str) or not value.strip():
        raise click.BadParameter("Model name must be a non-empty string.")
    # Optionally, you can add more checks here or call NeMo's get_supported_models
    return value

# --- Resource Shape/Memory Validation ---
GPU_RESOURCE_PATTERNS = [
    r'gpu\.(\d+)x([a-zA-Z0-9\-]+)',         # gpu.8xh200, gpu.4xh100, gpu.2xa100-40gb
    r'gpu\.([a-zA-Z0-9\-]+)\.(\w+)',        # gpu.a10.6xlarge
    r'gpu\.([a-zA-Z0-9\-]+)',               # gpu.a10, gpu.a100-40gb, gpu.h100-sxm
    r'(\d+)x([a-zA-Z0-9\-]+)',              # 8xh200, 4xh100, 2xa100-40gb
    r'(\d+)x?',                             # Just count: 8x, 8
]
def validate_resource_shape(ctx, param, value):
    if value is None:
        return value
    for pattern in GPU_RESOURCE_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return value
    examples = [
        "gpu.8xh200", "gpu.4xh100", "gpu.2xa100-40gb", "gpu.8xa100-80gb",
        "gpu.a10", "gpu.a10.6xlarge", "gpu.a100-40gb", "gpu.h100-sxm"
    ]
    raise click.BadParameter(
        f"Invalid resource shape format: '{value}'\n"
        f"Valid formats include: {', '.join(examples[:5])}...\n"
        f"Pattern should match: gpu.[count]x[type] or gpu.[type] or gpu.[type].[size]"
    )

def validate_resource_shape_or_memory(ctx, param, value):
    if not hasattr(ctx, '_resource_validation_params'):
        ctx._resource_validation_params = {}
    ctx._resource_validation_params[param.name] = value
    if len(ctx._resource_validation_params) == 2:
        resource_shape = ctx._resource_validation_params.get('resource_shape')
        memory_per_gpu = ctx._resource_validation_params.get('memory_per_gpu')
        if not resource_shape and not memory_per_gpu:
            raise click.BadParameter(
                "Either --resource-shape or --memory-per-gpu must be provided.\n"
                "Examples:\n"
                "  --resource-shape gpu.8xh200\n"
                "  --memory-per-gpu 141.0"
            )
    if param.name == 'resource_shape' and value:
        return validate_resource_shape(ctx, param, value)
    return value

# Custom click types for robust multiple value handling
class IntListType(click.ParamType):
    name = "int_list"
    def convert(self, value, param, ctx):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if ',' in value:
                try:
                    result = []
                    for x in value.split(','):
                        x = x.strip()
                        if x:
                            int_val = int(x)
                            if int_val <= 0:
                                self.fail(f"All values must be positive integers, got: {int_val}", param, ctx)
                            result.append(int_val)
                    return result
                except ValueError as e:
                    self.fail(f"Invalid integer in list '{value}': {e}", param, ctx)
            else:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        self.fail(f"Value must be a positive integer, got: {int_val}", param, ctx)
                    return [int_val]
                except ValueError:
                    self.fail(f"Invalid integer: '{value}'", param, ctx)
        if isinstance(value, int):
            if value <= 0:
                self.fail(f"Value must be a positive integer, got: {value}", param, ctx)
            return [value]
        self.fail(f"Invalid value type: {type(value)}", param, ctx)

class IntListOrAutoType(click.ParamType):
    name = "int_list_or_auto"
    def convert(self, value, param, ctx):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.lower() == 'auto':
                return 'auto'
            if ',' in value:
                try:
                    result = []
                    for x in value.split(','):
                        x = x.strip()
                        if x:
                            if x.lower() == 'auto':
                                self.fail(f"Cannot mix 'auto' with specific values in '{value}'", param, ctx)
                            int_val = int(x)
                            if int_val <= 0:
                                self.fail(f"All values must be positive integers, got: {int_val}", param, ctx)
                            result.append(int_val)
                    return result
                except ValueError as e:
                    self.fail(f"Invalid integer in list '{value}': {e}", param, ctx)
            else:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        self.fail(f"Value must be a positive integer, got: {int_val}", param, ctx)
                    return [int_val]
                except ValueError:
                    self.fail(f"Invalid value: '{value}'. Use 'auto' or positive integers.", param, ctx)
        if isinstance(value, int):
            if value <= 0:
                self.fail(f"Value must be a positive integer, got: {value}", param, ctx)
            return [value]
        self.fail(f"Invalid value type: {type(value)}", param, ctx)

INT_LIST = IntListType()
INT_LIST_OR_AUTO = IntListOrAutoType()

def common_options(f):
    f = click.option("--model", type=str, required=True, callback=validate_model_callback, help="[REQUIRED] Model to pretrain.")(f)
    f = click.option("--mount-from", type=str, required=True, help="[REQUIRED] Mount source.")(f)
    f = click.option("--mount-source-path", type=str, required=True, help="[REQUIRED] Mount source path.")(f)
    f = click.option("--mount-path", type=str, required=True, help="[REQUIRED] Mount destination path.")(f)
    f = click.option("--launcher-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")(f)
    return f

def config_model_options(f):
    f = click.option("--config-dir", type=str, required=True, help="[REQUIRED] Directory to save/generated configurations.")(f)
    f = click.option("--model", type=str, required=True, callback=validate_model_callback, help="[REQUIRED] Model to pretrain.")(f)
    return f

def batch_size_options(f):
    f = click.option("--micro-batch-sizes", type=INT_LIST_OR_AUTO, default="1,2,4", help="Micro batch sizes (comma-separated or 'auto').")(f)
    f = click.option("--global-batch-sizes", type=INT_LIST_OR_AUTO, default="512", help="Global batch sizes (comma-separated or 'auto').")(f)
    return f

def parallelism_options(f):
    f = click.option("--tensor-parallel-sizes", type=INT_LIST, default="1,2", help="Tensor parallel sizes (comma-separated).")(f)
    f = click.option("--pipeline-parallel-sizes", type=INT_LIST_OR_AUTO, default="1,2", help="Pipeline parallel sizes (comma-separated or 'auto').")(f)
    f = click.option("--context-parallel-sizes", type=INT_LIST, default="1,2", help="Context parallel sizes (comma-separated).")(f)
    f = click.option("--expert-parallel-sizes", type=INT_LIST, default="1", help="Expert parallel sizes (comma-separated).")(f)
    f = click.option("--virtual-pipeline-model-parallel-sizes", type=INT_LIST, default="1,2", help="Virtual pipeline parallel sizes (comma-separated).")(f)
    return f

def dynamic_executor_options(f):
    f = click.option("--container-image", type=str, default="nvcr.io/nvidia/nemo:25.04", help="Docker container image to use.")(f)
    f = click.option("--nemo-run-dir", type=str, default="/nemo-workspace/nemo-run", help="Directory for nemo-run.")(f)
    f = click.option("--hf-token", type=str, default=None, help="HuggingFace token (optional).") (f)
    f = click.option("--wandb-api-key", type=str, default=None, help="Weights & Biases API key (optional).") (f)
    f = click.option("--torch-home", type=str, default="/nemo-workspace/.cache", help="PyTorch cache directory.")(f)
    f = click.option("--pythonpath", type=str, default="/nemo-workspace/nemo-run:$PYTHONPATH", help="Python path configuration.")(f)
    return f

@click_group()
def autotune():
    """
    AutoTuner for model throughput on DGX Cloud Lepton.
    This CLI is a thin wrapper over NeMo's autotuner.
    """
    try:
        from nemo.collections.llm.tools.autotuner import runner as autotuner_runner
        from nemo.collections.llm.tools.autotuner.args import AutoTuneArgs
    except ImportError:
        console.print("[red]Error: NeMo autotuner is not available. Please install NeMo.[/red]")
        sys.exit(1)

@autotune.command()
@config_model_options
@common_options
@batch_size_options
@parallelism_options
@dynamic_executor_options
@click.option("--nodes", type=int, required=True, callback=validate_positive_int, help="[REQUIRED] Number of nodes for training.")
@click.option("--gpus-per-node", type=int, required=True, callback=validate_positive_int, help="[REQUIRED] GPUs per node.")
@click.option("--resource-shape", type=str, default=None, callback=validate_resource_shape_or_memory, help="GPU resource shape. Examples: gpu.8xh200, gpu.4xh100, gpu.a100-40gb, gpu.2xa100-80gb")
@click.option("--memory-per-gpu", type=float, default=None, callback=validate_resource_shape_or_memory, help="Custom GPU memory in GB (alternative to --resource-shape)")
@click.option("--max-model-parallel-size", type=int, default=32, callback=validate_positive_int, help="Maximum model parallel size.")
@click.option("--min-model-parallel-size", type=int, default=1, callback=validate_positive_int, help="Minimum model parallel size.")
@click.option("--max-steps-per-run", type=int, default=10, callback=validate_positive_int, help="Maximum steps per run for testing.")
@click.option("--max-minutes-per-run", type=int, default=10, callback=validate_positive_int, help="Maximum minutes per run for testing.")
@click.option("--num-tokens-in-b", type=int, default=15000, callback=validate_positive_int, help="Number of tokens in billions.")
@click.option("--vocab-size", type=int, default=32000, callback=validate_positive_int, help="Vocabulary size.")
@click.option("--seq-length", type=int, default=8192, callback=validate_positive_int, help="Sequence length for the model.")
@click.option("--val-check-interval", type=int, default=50, callback=validate_positive_int, help="Validation check interval.")
@click.option("--max-steps", type=int, default=10, callback=validate_positive_int, help="Maximum training steps.")
@click.option("--logs-subdir", type=str, required=True, help="[REQUIRED] Logs subdirectory relative to mount-path.")
@click.option("--launcher-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")
@click.option("--training-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")
def generate(**kwargs):
    """Generate AutoTune configurations for NeMo pretraining."""
    try:
        args_dict = {}
        for key, value in kwargs.items():
            snake_key = key.replace('-', '_')
            args_dict[snake_key] = value
        
        result = launch_generate_remote(args_dict, kwargs['launcher_node_group'], kwargs['training_node_group'],
                                      kwargs['mount_from'], kwargs['mount_source_path'], kwargs['mount_path'])
        console.print(f"[green]Configuration generation completed![/green]")
    except Exception as e:
        console.print(f"[red]Error generating configurations: {e}[/red]")
        logger.error(f"Configuration generation failed: {e}")
        sys.exit(1)

@autotune.command()
@config_model_options
@click.option("--launcher-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")
@click.option("--training-node-group", type=str, required=True, help="[REQUIRED] Node group for training jobs (GPU jobs).")
@click.option("--sequential", is_flag=True, default=False, help="Run configurations sequentially instead of in parallel.")
@click.option("--run-all", is_flag=True, default=False, help="Run all configurations including those with potential CUDA OOM risk.")
@click.option("--mount-from", type=str, required=True, help="[REQUIRED] Mount source.")
@click.option("--mount-source-path", type=str, required=True, help="[REQUIRED] Mount source path.")
@click.option("--mount-path", type=str, required=True, help="[REQUIRED] Mount destination path.")
def run(config_dir, model, sequential, run_all, launcher_node_group, training_node_group, mount_from, mount_source_path, mount_path):
    """Run AutoTune pretraining with generated configurations."""
    try:
        result = launch_run_remote(config_dir, model, mount_from, mount_source_path, mount_path, launcher_node_group, training_node_group, sequential, run_all)
        console.print(f"[green]AutoTune pretraining completed![/green]")
    except Exception as e:
        console.print(f"[red]Error running AutoTune pretraining: {e}[/red]")
        sys.exit(1)

@autotune.command()
@config_model_options
@click.option("--launcher-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")
@click.option("--path", "-p", type=str, required=True, help="[REQUIRED] Path to AutoConfigurator logs directory.")
@click.option("--log-prefix", type=str, default="", help="Log file prefix to search for (default: '')")
@click.option("--top-n", type=int, default=5, help="Number of top configurations to display (default: 5)")
@click.option("--force-reconstruct", is_flag=True, default=False, help="Force reconstruction of config objects")
@click.option("--cost-per-gpu-hour", type=float, default=3.0, help="Cost per GPU per hour for cost analysis (default: 3.0)")
@click.option("--quiet", is_flag=True, default=False, help="Suppress verbose output")
@click.option("--mount-from", type=str, required=True, help="[REQUIRED] Mount source.")
@click.option("--mount-source-path", type=str, required=True, help="[REQUIRED] Mount source path.")
@click.option("--mount-path", type=str, required=True, help="[REQUIRED] Mount destination path.")
def results(config_dir, model, path, log_prefix, top_n, force_reconstruct, cost_per_gpu_hour, quiet, launcher_node_group, mount_from, mount_source_path, mount_path):
    """Analyze AutoTune results and display performance analysis."""
    try:
        result = launch_results_remote(config_dir, model, path, log_prefix, mount_from, mount_source_path, mount_path, launcher_node_group, top_n, force_reconstruct, cost_per_gpu_hour, quiet)
        console.print(f"[green]Results analysis completed![/green]")
    except Exception as e:
        console.print(f"[red]Error analyzing results: {e}[/red]")
        sys.exit(1)

@autotune.command()
@config_model_options
@click.option("--launcher-node-group", type=str, required=True, help="[REQUIRED] Node group for launcher jobs (CPU jobs).")
@click.option("--mount-from", type=str, required=True, help="[REQUIRED] Mount source.")
@click.option("--mount-source-path", type=str, required=True, help="[REQUIRED] Mount source path.")
@click.option("--mount-path", type=str, required=True, help="[REQUIRED] Mount destination path.")
def list_configs(config_dir, model, launcher_node_group, mount_from, mount_source_path, mount_path):
    """List generated AutoTune configurations with detailed status."""
    try:
        result = launch_list_configs_remote(config_dir, model, mount_from, mount_source_path, mount_path, launcher_node_group)
        console.print(f"[green]Configuration listing completed![/green]")
    except Exception as e:
        console.print(f"[red]Error listing configs: {e}[/red]")
        sys.exit(1)

@autotune.command(name="list-models")
def list_models():
    """List all supported models for AutoTune."""
    try:
        list_models_impl()
        console.print(f"[green]Models listing completed![/green]")
    except Exception as e:
        console.print(f"[red]Error listing models: {e}[/red]")
        sys.exit(1)

def add_command(cli_group):
    """Add the autotune command group to the main CLI."""
    cli_group.add_command(autotune)
