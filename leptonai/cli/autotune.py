import pickle
import base64
import re
import click
import sys
import os
import json
import datetime
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from loguru import logger

from .util import (
    console,
    click_group,
)

from leptonai.api.v2.autotune import (
    generate_recipe_configs,
    run_pretraining_only,
    check_cuda_oom_risk,
    validate_configurations_memory,
    estimate_model_memory_usage_conservative,
    lepton_executor,
)

from leptonai.util.autotune import (
    validate_all_configs,
    check_config_matches,
    extract_all_values,          
    extract_gpu_specs_unified,
    create_log_dir_name,
    get_supported_models,
    validate_model_support,
)

# Check NeMo availability
try:
    from nemo.collections.llm.tools.auto_configurator import get_results
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False

from .autotune_display import (
    _display_memory_analysis,
    _display_configs_table,
    display_performance_analysis,
)

console = Console()

@contextmanager
def capture_output_to_file(output_file: str, mode: str = 'w', show_in_terminal: bool = True):
    """
    Context manager to capture all console output and redirect to file.
    
    Args:
        output_file: Path to output file
        mode: File mode ('w' for write, 'a' for append)
        show_in_terminal: Whether to also show output in terminal
    """
    if output_file:
        # Only create directory if there is a directory path
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Store original stdout and console
        original_stdout = sys.stdout
        original_console = console
        
        try:
            with open(output_file, mode) as f:
                if show_in_terminal:
                    # Create a console that writes to both file and terminal
                    file_console = Console(file=f, force_terminal=True)
                else:
                    # Create a console that only writes to file
                    file_console = Console(file=f, force_terminal=False)
                
                # Replace the global console temporarily
                import leptonai.cli.autotune_display
                leptonai.cli.autotune_display.console = file_console
                
                # Also capture stdout for any print statements
                sys.stdout = f
                
                yield file_console
                
        finally:
            # Restore original stdout and console
            sys.stdout = original_stdout
            leptonai.cli.autotune_display.console = original_console
    else:
        yield console


def capture_all_output_to_file(output_file: str, show_in_terminal: bool = True):
    """
    Helper function to capture all output to a file with proper formatting.
    
    Args:
        output_file: Path to output file
        show_in_terminal: Whether to also show output in terminal
    
    Returns:
        Context manager for output capture
    """
    return capture_output_to_file(output_file, mode='w', show_in_terminal=show_in_terminal)


# ============================================================================
# GPU RESOURCE PATTERNS AND VALIDATION
# ============================================================================

GPU_RESOURCE_PATTERNS = [
    # Enhanced patterns to handle all the new formats
    r'gpu\.(\d+)x([a-zA-Z0-9\-]+)',         # gpu.8xh200, gpu.4xh100, gpu.2xa100-40gb
    r'gpu\.([a-zA-Z0-9\-]+)\.(\w+)',        # gpu.a10.6xlarge
    r'gpu\.([a-zA-Z0-9\-]+)',               # gpu.a10, gpu.a100-40gb, gpu.h100-sxm
    r'(\d+)x([a-zA-Z0-9\-]+)',              # 8xh200, 4xh100, 2xa100-40gb
    r'(\d+)x?',                             # Just count: 8x, 8
]

def validate_resource_shape(ctx, param, value):
    """Validate resource shape format against known patterns."""
    if value is None:
        return value
    
    # Check if it matches any of our known patterns
    for pattern in GPU_RESOURCE_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return value
    
    # If no pattern matches, show error with examples
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
    """Validate that either resource_shape or memory_per_gpu is provided."""
    # This is called for both resource_shape and memory_per_gpu
    # We need to check if at least one is provided after all params are processed
    if not hasattr(ctx, '_resource_validation_params'):
        ctx._resource_validation_params = {}
    
    ctx._resource_validation_params[param.name] = value
    
    # Check if we have both parameters processed
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
    
    # Apply resource_shape validation if this is the resource_shape parameter
    if param.name == 'resource_shape' and value:
        return validate_resource_shape(ctx, param, value)
    
    return value


# ============================================================================
# CUSTOM CLICK TYPES FOR ROBUST MULTIPLE VALUE HANDLING
# ============================================================================

class IntListType(click.ParamType):
    """Custom type for comma-separated integers with robust error handling."""
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
    """Custom type for comma-separated integers or 'auto' with robust error handling."""
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


# ============================================================================
# AUTOTUNE ARGS CLASS
# ============================================================================

class AutoTuneArgs:
    """Class to hold all AutoTune arguments and handle serialization."""
    
    def __init__(self, **kwargs):
        self.model = kwargs.get('model')
        self.nodes = kwargs.get('nodes')
        self.gpus_per_node = kwargs.get('gpus_per_node')
        self.tensor_parallel_sizes = kwargs.get('tensor_parallel_sizes', [1, 2])
        self.pipeline_parallel_sizes = kwargs.get('pipeline_parallel_sizes', 'auto')
        self.context_parallel_sizes = kwargs.get('context_parallel_sizes', [1, 2])
        self.expert_parallel_sizes = kwargs.get('expert_parallel_sizes', [1])
        self.virtual_pipeline_model_parallel_sizes = kwargs.get('virtual_pipeline_model_parallel_sizes', None)
        self.micro_batch_sizes = kwargs.get('micro_batch_sizes', 'auto')
        self.max_model_parallel_size = kwargs.get('max_model_parallel_size', 8)
        self.min_model_parallel_size = kwargs.get('min_model_parallel_size', 1)
        self.max_steps_per_run = kwargs.get('max_steps_per_run', 10)
        self.max_minutes_per_run = kwargs.get('max_minutes_per_run', 10)
        self.num_tokens_in_b = kwargs.get('num_tokens_in_b', 15000)
        self.vocab_size = kwargs.get('vocab_size', 32000)
        self.seq_length = kwargs.get('seq_length', 8192)
        self.global_batch_sizes = kwargs.get('global_batch_sizes', [512])
        if isinstance(self.global_batch_sizes, tuple):
            self.global_batch_sizes = list(self.global_batch_sizes)
        self.val_check_interval = kwargs.get('val_check_interval', 50)
        self.max_steps = kwargs.get('max_steps', 10)
        self.get_results = kwargs.get('get_results', False)
        self.sequential = kwargs.get('sequential', False)
        # dynamic properties for executor
        self.resource_shape = kwargs.get('resource_shape')
        self.container_image = kwargs.get('container_image', 'nvcr.io/nvidia/nemo:25.04')
        self.nemo_run_dir = kwargs.get('nemo_run_dir', '/nemo-workspace/nemo-run')
        self.mount_path = kwargs.get('mount_path')
        self.mount_from = kwargs.get('mount_from')
        self.node_group = kwargs.get('node_group')
        self.hf_token = kwargs.get('hf_token', None)
        self.wandb_api_key = kwargs.get('wandb_api_key', None)
        self.torch_home = kwargs.get('torch_home', '/nemo-workspace/.cache')
        self.pythonpath = kwargs.get('pythonpath', '/nemo-workspace/nemo-run:$PYTHONPATH')
        self.memory_per_gpu = kwargs.get('memory_per_gpu')
        self.logs_subdir = kwargs.get('logs_subdir')
        self.config_dir = kwargs.get('config_dir')
        
        # Metadata from generation results (populated after generate)
        self.metadata = kwargs.get('metadata', {})

    def _serialize_object(self, obj):
        """Serialize a Python object to base64-encoded pickle string."""
        try:
            pickled_data = pickle.dumps(obj)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            return {
                '_type': 'pickled_object',
                '_class': obj.__class__.__name__,
                '_module': obj.__class__.__module__,
                '_data': encoded_data
            }
        except Exception as e:
            logger.warning(f"Could not serialize object {type(obj).__name__}: {e}")
            return {
                '_type': 'serialization_failed',
                '_class': obj.__class__.__name__,
                '_error': str(e)
            }

    def _deserialize_object(self, obj_dict):
        """Deserialize a base64-encoded pickle string back to Python object."""
        if not isinstance(obj_dict, dict) or obj_dict.get('_type') != 'pickled_object':
            return obj_dict
        
        try:
            encoded_data = obj_dict['_data']
            pickled_data = base64.b64decode(encoded_data.encode('utf-8'))
            obj = pickle.loads(pickled_data)
            logger.debug(f"Successfully deserialized {obj_dict['_class']} object")
            return obj
        except Exception as e:
            logger.warning(f"Could not deserialize {obj_dict.get('_class', 'unknown')} object: {e}")
            return {
                '_type': 'deserialization_failed',
                '_class': obj_dict.get('_class', 'unknown'),
                '_error': str(e),
                '_original': obj_dict
            }

    def _process_metadata_for_serialization(self, metadata):
        """Process metadata to serialize complex objects."""
        processed = {}
        
        for key, value in metadata.items():
            if key in ['base_config', 'runner'] and value is not None:
                # Serialize complex objects
                processed[key] = self._serialize_object(value)
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                processed[key] = self._process_metadata_for_serialization(value)
            elif isinstance(value, list):
                # Process lists that might contain complex objects
                processed[key] = [
                    self._serialize_object(item) if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool))
                    else item for item in value
                ]
            else:
                # Keep simple types as-is
                processed[key] = value
                
        return processed

    def _process_metadata_for_deserialization(self, metadata):
        """Process metadata to deserialize complex objects."""
        processed = {}
        
        for key, value in metadata.items():
            if isinstance(value, dict) and value.get('_type') == 'pickled_object':
                # Deserialize complex objects
                processed[key] = self._deserialize_object(value)
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                processed[key] = self._process_metadata_for_deserialization(value)
            elif isinstance(value, list):
                # Process lists that might contain serialized objects
                processed[key] = [
                    self._deserialize_object(item) if isinstance(item, dict) and item.get('_type') == 'pickled_object'
                    else item for item in value
                ]
            else:
                # Keep simple types as-is
                processed[key] = value
                
        return processed

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        # Process metadata to handle complex objects
        processed_metadata = self._process_metadata_for_serialization(self.metadata)
        
        return {
            'model': self.model,
            'nodes': self.nodes,
            'gpus_per_node': self.gpus_per_node,
            'tensor_parallel_sizes': self.tensor_parallel_sizes,
            'pipeline_parallel_sizes': self.pipeline_parallel_sizes,
            'context_parallel_sizes': self.context_parallel_sizes,
            'expert_parallel_sizes': self.expert_parallel_sizes,
            'virtual_pipeline_model_parallel_sizes': self.virtual_pipeline_model_parallel_sizes,
            'micro_batch_sizes': self.micro_batch_sizes,
            'max_model_parallel_size': self.max_model_parallel_size,
            'min_model_parallel_size': self.min_model_parallel_size,
            'max_steps_per_run': self.max_steps_per_run,
            'max_minutes_per_run': self.max_minutes_per_run,
            'num_tokens_in_b': self.num_tokens_in_b,
            'vocab_size': self.vocab_size,
            'seq_length': self.seq_length,
            'global_batch_sizes': self.global_batch_sizes,
            'val_check_interval': self.val_check_interval,
            'max_steps': self.max_steps,
            'get_results': self.get_results,
            'sequential': self.sequential,
            # executor properties
            'resource_shape': self.resource_shape,
            'container_image': self.container_image,
            'nemo_run_dir': self.nemo_run_dir,
            'mount_path': self.mount_path,
            'mount_from': self.mount_from,
            'node_group': self.node_group,
            'hf_token': self.hf_token,
            'wandb_api_key': self.wandb_api_key,
            'torch_home': self.torch_home,
            'pythonpath': self.pythonpath,
            'memory_per_gpu': self.memory_per_gpu,
            'logs_subdir': self.logs_subdir,
            'config_dir': self.config_dir,
            'metadata': processed_metadata,
        }

    def get_full_logs_path(self):
        """Get the full logs path by combining mount_path and logs_subdir."""
        return os.path.join(self.mount_path, self.logs_subdir, self.model)
        
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary loaded from JSON."""
        instance = cls(**data)
        if 'metadata' in data:
            instance.metadata = instance._process_metadata_for_deserialization(data['metadata'])
        
        return instance

    def save_to_file(self, filepath):
        """Save arguments to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load_from_file(cls, filepath):
        """Load arguments from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def update_metadata(self, result):
        """Update metadata with generation results."""
        self.metadata = {
            'base_config_matches': result['base_config_matches'],
            'num_configs_generated': result['num_configs_generated'],
            'config_names': list(result['configs'].keys()),
            'generation_timestamp': datetime.datetime.now().isoformat(),
            'total_gpus': self.nodes * self.gpus_per_node,
            'base_config': result['base_config'],
            'runner': result['runner'],
            'memory_analysis': result.get('memory_analysis', {}),
        }

    def update_performance_results(self, performance_dict):
        """Update metadata with performance results."""
        self.metadata['performance_dict'] = performance_dict
        self.metadata['results_timestamp'] = datetime.datetime.now().isoformat()

    def get_performance_dict(self):
        """Get performance_dict from metadata."""
        return self.metadata.get('performance_dict')

    def has_performance_results(self):
        """Check if performance results are available."""
        return 'performance_dict' in self.metadata and self.metadata['performance_dict'] is not None

    def get_memory_analysis(self):
        """Get memory analysis from metadata."""
        return self.metadata.get('memory_analysis', {})

    def has_memory_analysis(self):
        """Check if memory analysis is available."""
        return 'memory_analysis' in self.metadata and self.metadata['memory_analysis']

    def save_with_metadata(self, filepath, result):
        """Save arguments with updated metadata to JSON file."""
        self.update_metadata(result)
        self.save_to_file(filepath)

    def get_base_config(self):
        """Get base_config from metadata, with fallback."""
        base_config = self.metadata.get('base_config')
        if isinstance(base_config, dict) and base_config.get('_type') == 'deserialization_failed':
            logger.warning("Base config deserialization failed, will need to reconstruct")
            return None
        return base_config

    def get_runner(self):
        """Get runner from metadata, with fallback."""
        runner = self.metadata.get('runner')
        if isinstance(runner, dict) and runner.get('_type') == 'deserialization_failed':
            logger.warning("Runner deserialization failed, will need to reconstruct")
            return None
        return runner

    def has_valid_objects(self):
        """Check if we have valid serialized objects."""
        base_config = self.get_base_config()
        runner = self.get_runner()
        return base_config is not None and runner is not None

    def get_executor_config(self):
        """Get executor configuration as a dictionary."""
        return {
            'resource_shape': self.resource_shape,
            'container_image': self.container_image,
            'nemo_run_dir': self.nemo_run_dir,
            'mount_path': self.mount_path,
            'mount_from': self.mount_from,
            'node_group': self.node_group,
            'hf_token': self.hf_token,
            'wandb_api_key': self.wandb_api_key,
            'torch_home': self.torch_home,
            'pythonpath': self.pythonpath,
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_args_file_path(model, config_dir):
    """Get the standard path for the args file."""
    return os.path.join(config_dir, model, "args.json")


def update_args_with_generation_metadata(model_name, result, config_dir):
    """Update the args.json file with generation metadata."""
    args_file_path = get_args_file_path(model_name, config_dir)
    
    # Load existing args
    args = AutoTuneArgs.load_from_file(args_file_path)
    
    # Update with metadata and save
    args.save_with_metadata(args_file_path, result)
    
    return args_file_path


def update_args_with_performance_results(model_name, performance_dict, config_dir):
    """Update the args.json file with performance results."""
    args_file_path = get_args_file_path(model_name, config_dir)
    
    # Load existing args
    args = AutoTuneArgs.load_from_file(args_file_path)
    
    # Update with performance results and save
    args.update_performance_results(performance_dict)
    args.save_to_file(args_file_path)
    
    return args_file_path


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def validate_model_callback(ctx, param, value):
    """Validate that the specified model exists in the llm module."""
    if value is None:
        return value
    
    try:
        is_valid, error_msg = validate_model_support(value)
        if not is_valid:
            supported_models = get_supported_models()
            console.print(f"[red]Model '{value}' is not supported.[/red]")
            console.print(f"[yellow]Supported models:[/yellow] {', '.join(supported_models[:10])}{'...' if len(supported_models) > 10 else ''}")
            console.print("[yellow]For the complete list of supported models, please check:[/yellow]")
            console.print("[link]https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py[/link]")
            raise click.BadParameter(f"Unsupported model: {value}")
        return value
    except Exception as e:
        if "Unsupported model" in str(e):
            raise e
        else:
            console.print(f"[red]Error validating model '{value}': {e}[/red]")
            console.print("[yellow]Please check supported models at:[/yellow]")
            console.print("[link]https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py[/link]")
            raise click.BadParameter(f"Error validating model: {e}")


def validate_positive_int(ctx, param, value):
    """Validate that a value is a positive integer."""
    if value is None:
        return value
    
    if value <= 0:
        raise click.BadParameter(f"{param.name} must be a positive integer, got: {value}")
    
    return value


def validate_positive_float(ctx, param, value):
    """Validate that a value is a positive float."""
    if value is None:
        return value
    
    if value <= 0:
        raise click.BadParameter(f"{param.name} must be a positive number, got: {value}")
    
    return value


def _load_args_from_config_dir(config_dir, model=None):
    """Load args from config directory, with model auto-detection if needed."""
    if not os.path.exists(config_dir):
        console.print(f"[red]Config directory not found: {config_dir}[/red]")
        console.print("[yellow]Tip: Run 'lep autotune generate' first to create configurations[/yellow]")
        sys.exit(1)
    
    # If model not provided, try to infer from directory structure
    if not model:
        subdirs = [d for d in os.listdir(config_dir) if os.path.isdir(os.path.join(config_dir, d))]
        if len(subdirs) == 1:
            model = subdirs[0]
            console.print(f"[blue]Auto-detected model: {model}[/blue]")
        elif len(subdirs) > 1:
            console.print(f"[yellow]Multiple models found. Please specify --model. Available: {', '.join(subdirs)}[/yellow]")
            sys.exit(1)
        elif len(subdirs) == 0:
            console.print(f"[red]No model directories found in: {config_dir}[/red]")
            console.print("[yellow]Tip: Run 'lep autotune generate' first to create configurations[/yellow]")
            sys.exit(1)
    
    args_file_path = get_args_file_path(model, config_dir)
    if not os.path.exists(args_file_path):
        console.print(f"[red]Arguments file not found: {args_file_path}[/red]")
        console.print("[yellow]Tip: Run 'lep autotune generate' first to create configurations[/yellow]")
        sys.exit(1)
    
    return AutoTuneArgs.load_from_file(args_file_path)


def calculate_performance_analysis(performance_dict, args, total_tokens, cost_per_node_hour):
    """Calculate performance and cost analysis for all configurations."""
    if not performance_dict:
        return None
    total_gpus = args.nodes * args.gpus_per_node
    config_analysis = {}
    for config_name, config_data in performance_dict.items():
        time_per_step = config_data.get('time_per_global_step', 0)
        m_tflops_gpu = config_data.get('m_tflops_gpu', 0)
        extracted_values = extract_all_values(config_name)
        gbs = extracted_values.get('gbs')
        if gbs is None:
            gbs = args.global_batch_sizes[0] if args.global_batch_sizes else 512
        tokens_per_step = args.seq_length * gbs
        total_steps = total_tokens / tokens_per_step
        total_training_time_seconds = time_per_step * total_steps
        total_training_time_hours = total_training_time_seconds / 3600
        total_cost = total_training_time_hours * cost_per_node_hour * args.nodes
        config_analysis[config_name] = {
            **config_data,
            'gbs': gbs,
            'tokens_per_step': tokens_per_step,
            'total_steps': total_steps,
            'total_training_time_hours': total_training_time_hours,
            'total_training_time_days': total_training_time_hours / 24,
            'total_cost': total_cost,
            'cost_per_tflop': total_cost / (m_tflops_gpu * total_gpus) if m_tflops_gpu > 0 else float('inf')
        }
    sorted_configs = sorted(
        config_analysis.items(),
        key=lambda x: x[1].get('total_training_time_hours', float('inf')),
        reverse=False
    )
    return {
        'config_analysis': config_analysis,
        'sorted_configs': sorted_configs,
        'args': args
    }


# ============================================================================
# CLICK COMMAND GROUP AND COMMANDS
# ============================================================================

def common_options(f):
    f = click.option("--model", type=str, required=True, callback=validate_model_callback, help="[REQUIRED] Model to pretrain.")(f)
    f = click.option("--nodes", "-n", type=int, required=True, callback=validate_positive_int, help="[REQUIRED] Number of nodes for training.")(f)
    f = click.option("--gpus-per-node", type=int, required=True, callback=validate_positive_int, help="[REQUIRED] GPUs per node.")(f)
    f = click.option("--mount-path", type=str, required=True, help="[REQUIRED] Mount path in container.")(f)
    f = click.option("--mount-from", type=str, required=True, help="[REQUIRED] Mount source.")(f)
    f = click.option("--node-group", type=str, required=True, help="[REQUIRED] Node group for execution.")(f)
    f = click.option("--logs-subdir", type=str, required=True, help="[REQUIRED] Logs subdirectory relative to mount-path. Example: autoconfigurator/logs")(f)
    return f

def config_model_options(f):
    f = click.option("--config-dir", type=str, required=True, help="[REQUIRED] Directory to save/generated configurations.")(f)
    f = click.option("--model", type=str, required=True, callback=validate_model_callback, help="[REQUIRED] Model to pretrain.")(f)
    return f

def batch_size_options(f):
    f = click.option("--micro-batch-sizes", type=INT_LIST_OR_AUTO, default="1,2,4", help="Micro batch sizes. Use 'auto' or comma-separated: --micro-batch-sizes 1,2,4,8")(f)
    f = click.option("--global-batch-sizes", type=INT_LIST_OR_AUTO, default="512", help="Global batch sizes. Use 'auto' or comma-separated: --global-batch-sizes 64,128,256,512")(f)
    return f

def parallelism_options(f):
    f = click.option("--tensor-parallel-sizes", type=INT_LIST, default="1,2", help="Tensor parallel sizes. Use comma-separated: --tensor-parallel-sizes 4,8,16")(f)
    f = click.option("--pipeline-parallel-sizes", type=INT_LIST_OR_AUTO, default="1,2", help="Pipeline parallel sizes. Use 'auto' or comma-separated: --pipeline-parallel-sizes 1,2,4")(f)
    f = click.option("--context-parallel-sizes", type=INT_LIST, default="1,2", help="Context parallel sizes. Use comma-separated: --context-parallel-sizes 1,2,4")(f)
    f = click.option("--expert-parallel-sizes", type=INT_LIST, default="1", help="Expert parallel sizes. Use comma-separated: --expert-parallel-sizes 1,2,4")(f)
    f = click.option("--virtual-pipeline-model-parallel-sizes", type=INT_LIST, default=None, help="Virtual pipeline sizes. Use comma-separated: --virtual-pipeline-model-parallel-sizes 2,4")(f)
    return f

def dynamic_executor_options(f):
    f = click.option("--container-image", type=str, default="nvcr.io/nvidia/nemo:25.02", help="Docker container image to use.")(f)
    f = click.option("--nemo-run-dir", type=str, default="/nemo-workspace/nemo-run", help="Directory for nemo-run.")(f)
    f = click.option("--hf-token", type=str, default=None, help="HuggingFace token (optional).") (f)
    f = click.option("--wandb-api-key", type=str, default=None, help="Weights & Biases API key (optional).") (f)
    f = click.option("--torch-home", type=str, default="/nemo-workspace/.cache", help="PyTorch cache directory.")(f)
    f = click.option("--pythonpath", type=str, default="/nemo-workspace/nemo-run:$PYTHONPATH", help="Python path configuration.")(f)
    return f

@click_group()
def autotune():
    """
    AutoTune configurations for model throughput on DGX Cloud Lepton.

    AutoTune automatically generates and tests multiple training configurations
    to find optimal parallelism settings for your model and hardware setup to maximize pre training model throughput.
    
    For supported models, see: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py
    """
    if not NEMO_AVAILABLE:
        console.print("[red]Error: NeMo is not properly installed or available.[/red]")
        console.print("Please install NeMo before using AutoTune features.")
        sys.exit(1)


@autotune.command()
@config_model_options
@common_options
@batch_size_options
@parallelism_options
@dynamic_executor_options
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
def generate(**kwargs):
    """Generate AutoTune configurations for NeMo pretraining."""
    console.print(f"Generating AutoTune configurations for model: [bold]{kwargs['model']}[/bold]")
    
    # print the received values for debugging
    console.print(f"[blue]Received parameters:[/blue]")
    console.print(f"  Global batch sizes: {kwargs['global_batch_sizes']}")
    console.print(f"  Tensor parallel sizes: {kwargs['tensor_parallel_sizes']}")
    console.print(f"  Pipeline parallel sizes: {kwargs['pipeline_parallel_sizes']}")
    console.print(f"  Context parallel sizes: {kwargs['context_parallel_sizes']}")
    console.print(f"  Expert parallel sizes: {kwargs['expert_parallel_sizes']}")
    console.print(f"  Micro batch sizes: {kwargs['micro_batch_sizes']}")
    
    # ONE FUNCTION CALL to get all info: GPU specs, model size, etc.
    gpu_type, gpu_count, gpu_memory_gb = extract_gpu_specs_unified(kwargs['resource_shape'], kwargs.get('memory_per_gpu'))
    model_info = extract_all_values(kwargs['model'])
    model_size_b = model_info.get('model_size_b')
    
    console.print(f" Resource: [blue]{kwargs['resource_shape']}[/blue] ({gpu_type.upper()}, {gpu_memory_gb}GB per GPU)")
    if model_size_b:
        console.print(f" Model: [cyan]{kwargs['model']}[/cyan] ({model_size_b}B parameters)")
    else:
        console.print(f" Model: [cyan]{kwargs['model']}[/cyan]")
    
    args = AutoTuneArgs(**kwargs)
    
    try:
        console.print("[yellow]Validating configuration parameters...[/yellow]")
        is_valid, error_msg = validate_all_configs(args)
        if not is_valid:
            console.print("[red]Configuration validation failed:[/red]")
            console.print(f"   {error_msg}")
            sys.exit(1)
        
        console.print("[green]Configuration validation passed![/green]")
        
        args_file_path = get_args_file_path(args.model, kwargs['config_dir'])
        args.save_to_file(args_file_path)
        console.print(f"[blue]Arguments saved to: {args_file_path}[/blue]")
        
        console.print("[yellow]Generating configurations...[/yellow]")

        result = generate_recipe_configs(args)

        update_args_with_generation_metadata(args.model, result, kwargs['config_dir'])
        console.print(f"[blue]Metadata and objects saved to: {args_file_path}[/blue]")
        
        console.print("[green]Configurations generated successfully![/green]")
        console.print(f"Saved to: {os.path.join(kwargs['config_dir'], args.model)}")
        console.print(f"Generated {result['num_configs_generated']} configurations")
        
        memory_analysis = result.get('memory_analysis', {})
        if memory_analysis:
            oom_configs = [name for name, analysis in memory_analysis.items() if analysis.get("will_oom", False)]
            safe_configs = [name for name, analysis in memory_analysis.items() if not analysis.get("will_oom", False)]
            
            console.print(f"\n[cyan]Memory Analysis Summary:[/cyan]")
            console.print(f"Configurations that will run safely: {len(safe_configs)}")
            if oom_configs:
                console.print(f"⚠ Configurations flagged with potential CUDA OOM: {len(oom_configs)}")
                console.print(f"[yellow]Flagged configs: \n {', '.join(oom_configs)}[/yellow]")
                console.print(f"[dim]These will be SKIPPED during 'lep autotune run' (use --run-all to force)[/dim]")
            
            console.print(f"\n[blue]All configurations have been generated and saved[/blue]")
            console.print(f"[blue]Use 'lep autotune list-configs' to see detailed memory analysis[/blue]")
        
        if result['base_config_matches']:
            console.print(f"[blue]Found {len(result['base_config_matches'])} matching configurations: {', '.join(result['base_config_matches'])}[/blue]")
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error generating configurations: {e}[/red]")
        logger.error(f"Configuration generation failed: {e}")
        sys.exit(1)


@autotune.command()
@config_model_options
@click.option("--sequential", is_flag=True, default=False, help="Run configurations sequentially instead of in parallel.")
@click.option("--run-all", "--run_all", "run_all", is_flag=True, default=False, help="Run all configurations including those with potential CUDA OOM risk.")
def run(config_dir, model, sequential, run_all):
    """Run AutoTune pretraining with generated configurations."""
    
    try:
        args = _load_args_from_config_dir(config_dir, model)
        args.sequential = sequential
        
        console.print(f"Starting AutoTune pretraining for model: [bold]{args.model}[/bold]")
        console.print(f"Resource shape: [blue]{args.resource_shape}[/blue]")
        
        if run_all:
            console.print("[yellow]⚠ --run-all flag enabled: Will run ALL configurations including potential OOM ones[/yellow]")
        else:
            console.print("[blue] Default mode: Will skip configurations with potential CUDA OOM risk[/blue]")
            console.print("[dim](Use --run-all to run all configurations regardless of OOM risk)[/dim]")
        
        console.print("[yellow]Validating configuration parameters...[/yellow]")
        
        is_valid, error_msg = validate_all_configs(args)
        if not is_valid:
            console.print("[red]Configuration validation failed:[/red]")
            console.print(f"   {error_msg}")
            sys.exit(1)
        
        console.print("[green]Configuration validation passed![/green]")
        console.print("[yellow]Generating and running configurations...[/yellow]")
        
        config_result = generate_recipe_configs(args)
        memory_analysis = config_result.get('memory_analysis', {})
        
        if memory_analysis and not run_all:
            oom_configs = [name for name, analysis in memory_analysis.items() if analysis.get("will_oom", False)]
            safe_configs = [name for name, analysis in memory_analysis.items() if not analysis.get("will_oom", False)]
            
            console.print(f"\n[cyan] Memory Analysis Summary:[/cyan]")
            console.print(f"Safe configurations: {len(safe_configs)}")
            console.print(f"Potential OOM configurations: {len(oom_configs)}")
            
            if oom_configs:
                console.print(f"  [yellow]Configurations that will be SKIPPED: {', '.join(oom_configs)}[/yellow]")
                console.print(f"  [dim]Use --run-all to run these anyway[/dim]")
        
        run_result = run_pretraining_only(
            config_result['base_config'], 
            config_result['configs'], 
            config_result['base_config_matches'], 
            sequential,
            executor_config=args.get_executor_config(),
            memory_analysis=memory_analysis,
            run_all=run_all
        )
            
        if run_result['status'] == 'no_configs_to_run':
            console.print("[red] No configurations were run![/red]")
            console.print("[yellow]All configurations were filtered out due to potential CUDA OOM.[/yellow]")
            console.print("[yellow]Use --run-all flag to run them anyway, or adjust your parameters.[/yellow]")
            sys.exit(1)
        
        console.print("[green]AutoTune pretraining completed successfully![/green]")
        console.print(f"Total configurations: {run_result['total_configs']}")
        console.print(f"Configurations executed: {run_result['configs_run']}")
        
        if run_result['configs_skipped'] > 0:
            console.print(f"[yellow]⏭ Configurations skipped: {run_result['configs_skipped']}[/yellow]")
            skipped_list = list(run_result['skipped_configs'].keys())
            console.print(f"[yellow]Skipped configs: {', '.join(skipped_list)}[/yellow]")
        
        if config_result['base_config_matches']:
            console.print(f"[blue]Note: Base config was not run separately as it matches: {', '.join(config_result['base_config_matches'])}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error running AutoTune pretraining: {e}[/red]")
        logger.error(f"AutoTune pretraining failed: {e}")
        sys.exit(1)


@autotune.command()
@config_model_options
@click.option("--path", "-p", type=str, required=True, help="[REQUIRED] Path to AutoConfigurator logs directory.")
@click.option("--log-prefix", type=str, required=True, help="[REQUIRED] Log file prefix for result files.")
@click.option("--output-file", type=str, required=True, help="[REQUIRED] File path to save results.")
@click.option("--top-n", type=int, default=10, callback=validate_positive_int, help="Number of top configurations to display.")
@click.option("--force-reconstruct", is_flag=True, default=False, help="Force reconstruction instead of using saved objects.")
@click.option("--cost-per-node-hour", type=float, default=32.0, callback=validate_positive_float, help="Cost per node hour in USD (default: $32.0 for H100).")
@click.option("--quiet", is_flag=True, default=False, help="Only save to file, don't show output in terminal.")
def results(config_dir, model, path, log_prefix, output_file, top_n, force_reconstruct, cost_per_node_hour, quiet):
    """Collect, analyze, and display AutoConfigurator results in one step."""
    
    try:
        if not os.path.exists(path):
            console.print(f"[red]Logs directory not found: {path}[/red]")
            console.print("[yellow]Tip: Run 'lep autotune run' first to generate training logs[/yellow]")
            sys.exit(1)
            
        args = _load_args_from_config_dir(config_dir, model)
        
        # Use the context manager to capture ALL output to the file
        with capture_all_output_to_file(output_file, show_in_terminal=not quiet) as file_console:
            file_console.print("=" * 80)
            file_console.print("AUTOTUNE RESULTS - COMPLETE ANALYSIS")
            file_console.print("=" * 80)
            file_console.print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_console.print(f"Model: {args.model}")
            file_console.print(f"Logs path: {path}")
            file_console.print(f"Log prefix: {log_prefix}")
            file_console.print("=" * 80)
            
            file_console.print(f"Collecting AutoTune results from: [bold]{path}[/bold]")
            file_console.print(f"[blue]Loaded configuration for model: {args.model}[/blue]")
            file_console.print(f"  Resources: {args.nodes} nodes × {args.gpus_per_node} GPUs = {args.nodes * args.gpus_per_node} total GPUs")
            file_console.print(f"Resource shape: {args.resource_shape}")
            file_console.print(f"  Batch sizes: micro={args.micro_batch_sizes}, global={args.global_batch_sizes}")
            file_console.print(f"  Sequence length: {args.seq_length}")
            file_console.print(f"  Training: max_steps={args.max_steps}, val_check_interval={args.val_check_interval}")
            
            if not force_reconstruct and args.has_valid_objects():
                file_console.print("[blue]Using saved AutoConfigurator objects from args.json[/blue]")
                base_config = args.get_base_config()
                runner = args.get_runner()
                metadata = args.metadata
            else:
                if force_reconstruct:
                    file_console.print("[yellow]Force reconstruction requested - reconstructing AutoConfigurator configuration...[/yellow]")
                else:
                    file_console.print("[yellow]Saved objects not available - reconstructing AutoConfigurator configuration...[/yellow]")
                config_result = generate_recipe_configs(args)
                base_config = config_result['base_config']
                runner = config_result['runner']
                metadata = args.metadata
            
            file_console.print("[yellow]Analyzing training results...[/yellow]")
            
            # Get results directly (output will be captured by our context manager)
            file_console.print(f"Collecting AutoConfigurator results...")
            file_console.print(f"Displaying top {top_n} results:")
            
            base_config_matches = metadata.get('base_config_matches', [])
            if base_config_matches:
                file_console.print(f"Note: Base config is equivalent to: {', '.join(base_config_matches)}")
            
            performance_dict = get_results(
                base_config=base_config,
                train_config=runner,
                path_to_save=path,
                output_top_n=top_n,
                log_file_prefix=log_prefix,
            )
            
            file_console.print(f"Results collection completed. Total configs: {metadata.get('num_configs_generated')}, Base config matches: {len(base_config_matches)}")
            
            if performance_dict:
                file_console.print("[blue]Saving performance results to args.json...[/blue]")
                update_args_with_performance_results(args.model, performance_dict, config_dir)
                file_console.print("[blue]Performance results saved![/blue]")
            
            file_console.print(f"[green]Results analysis completed successfully![/green]")
            file_console.print(f"[green]Analyzed top {metadata.get('num_configs_generated', 'Unknown')} configurations[/green]")
            
            # --- Performance Analysis and Display ---
            if performance_dict:
                args = _load_args_from_config_dir(config_dir, model)
                total_tokens = args.num_tokens_in_b * 1_000_000_000
                analysis_data = calculate_performance_analysis(performance_dict, args, total_tokens, cost_per_node_hour)
                display_performance_analysis(analysis_data)
            
            file_console.print("=" * 80)
            file_console.print("END OF AUTOTUNE RESULTS")
            file_console.print("=" * 80)
        
        # Show summary in terminal (unless quiet mode)
        if not quiet:
            console.print(f"[green]✅ Results analysis completed successfully![/green]")
            console.print(f"[green]📁 All results saved to: {output_file}[/green]")
            console.print(f"[green]📊 Analyzed {metadata.get('num_configs_generated', 'Unknown')} configurations[/green]")
        else:
            console.print(f"[green]✅ Results saved to: {output_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error during results analysis: {e}[/red]")
        logger.error(f"Results analysis failed: {e}")
        sys.exit(1)


@autotune.command()
@config_model_options
def list_configs(config_dir, model):
    """List generated AutoTune configurations with detailed status."""
    try:
        args = _load_args_from_config_dir(config_dir, model)
        model_config_dir = os.path.join(config_dir, args.model)
        
        console.print(f"Configurations for model: [bold]{args.model}[/bold]")
        console.print(f"Location: {model_config_dir}")
        
        _display_configs_table(model_config_dir, args.model)
        
    except Exception as e:
        console.print(f"[red]Error listing configs: {e}[/red]")
        sys.exit(1)


@autotune.command(name="list-models")
def list_models():
    """List all supported models for AutoTune."""
    try:
        supported_models = get_supported_models()
        
        console.print("[green]Supported AutoTune Models:[/green]")
        console.print("[link]Reference: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py[/link]")
        console.print()
        
        table = Table(show_header=True, show_lines=False, title="Available Models")
        table.add_column("Model Name", style="green")
        table.add_column("Description", style="cyan")
        
        for model in supported_models:
            description = "Language model"
            if "nemotron" in model.lower():
                description = "NVIDIA Nemotron model"
            elif "llama" in model.lower():
                description = "LLaMA-based model"
            elif "mistral" in model.lower():
                description = "Mistral model"
            elif "mixtral" in model.lower():
                description = "Mixtral MoE model"
            
            table.add_row(model, description)
        
        console.print(table)
        console.print(f"\n[green]Total: {len(supported_models)} supported models[/green]")
        
    except Exception as e:
        console.print(f"[red]Error listing models: {e}[/red]")
        console.print("[link]Please check: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py[/link]")
        sys.exit(1)


def add_command(cli_group):
    """Add the autotune command group to the main CLI."""
    cli_group.add_command(autotune)
