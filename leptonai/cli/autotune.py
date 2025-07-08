import pickle
import base64
from typing import List, Optional
import click
import sys
import os
import json
import datetime

from loguru import logger
from rich.table import Table

from .util import (
    console,
    click_group,
)

# Import the improved autotune functionality
from leptonai.api.v2.autotune_core_test import (
    generate_recipe_configs,
    run_pretraining_only,
    get_results_with_output,
    check_cuda_oom_risk,
    validate_configurations_memory,
)

# ========== OPTIMIZED IMPORTS - ONE FUNCTION TO RULE THEM ALL ==========
from leptonai.api.v2.autotune_utils_test import (
    validate_all_configs,
    check_config_matches,
    extract_all_values,              # THE ONE FUNCTION TO RULE THEM ALL
    extract_gpu_specs,               # Only separate function needed 
    create_log_dir_name,
    get_supported_models,
    validate_model_support,
)

# Import required NeMo modules
try:
    from nemo.collections import llm
    import nemo_run as run
    NEMO_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import NeMo modules: {e}")
    logger.error("Please ensure NeMo is properly installed")
    NEMO_AVAILABLE = False


class AutoTuneArgs:
    """Class to hold all AutoTune arguments and handle serialization."""
    
    def __init__(self, **kwargs):
        # Set defaults for training parameters
        self.model = kwargs.get('model', 'nemotron3_4b')
        self.nodes = kwargs.get('nodes', 1)
        self.gpus_per_node = kwargs.get('gpus_per_node', 8)
        self.tensor_parallel_sizes = kwargs.get('tensor_parallel_sizes', [1, 2])
        self.pipeline_parallel_sizes = kwargs.get('pipeline_parallel_sizes', 'auto')
        self.context_parallel_sizes = kwargs.get('context_parallel_sizes', [1, 2])
        self.virtual_pipeline_model_parallel_sizes = kwargs.get('virtual_pipeline_model_parallel_sizes', None)
        self.micro_batch_sizes = kwargs.get('micro_batch_sizes', 'auto')
        self.max_model_parallel_size = kwargs.get('max_model_parallel_size', 8)
        self.min_model_parallel_size = kwargs.get('min_model_parallel_size', 1)
        self.max_steps_per_run = kwargs.get('max_steps_per_run', 10)
        self.max_minutes_per_run = kwargs.get('max_minutes_per_run', 10)
        self.num_tokens_in_b = kwargs.get('num_tokens_in_b', 840)
        self.vocab_size = kwargs.get('vocab_size', 32000)
        self.seq_length = kwargs.get('seq_length', 8192)
        self.global_batch_sizes = kwargs.get('global_batch_sizes', [512])
        if isinstance(self.global_batch_sizes, tuple):
            self.global_batch_sizes = list(self.global_batch_sizes)
        self.val_check_interval = kwargs.get('val_check_interval', 50)
        self.max_steps = kwargs.get('max_steps', 10)
        self.get_results = kwargs.get('get_results', False)
        self.sequential = kwargs.get('sequential', False)
        
        # New dynamic executor properties
        self.resource_shape = kwargs.get('resource_shape', 'gpu.8xh200')
        self.container_image = kwargs.get('container_image', 'nvcr.io/nvidia/nemo:25.02')
        self.nemo_run_dir = kwargs.get('nemo_run_dir', '/nemo-workspace/nemo-run')
        self.mount_path = kwargs.get('mount_path', '/nemo-workspace')
        self.mount_from = kwargs.get('mount_from', 'node-nfs:shared')
        self.node_group = kwargs.get('node_group', 'nebius-h200-01')
        self.hf_token = kwargs.get('hf_token', None)
        self.wandb_api_key = kwargs.get('wandb_api_key', None)
        self.torch_home = kwargs.get('torch_home', '/nemo-workspace/.cache')
        self.pythonpath = kwargs.get('pythonpath', '/nemo-workspace/nemo-run:$PYTHONPATH')
        self.memory_per_gpu = kwargs.get('memory_per_gpu', None)  # Custom GPU memory override
        
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
            # New executor properties
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
            'metadata': processed_metadata,
        }

    @classmethod
    def from_dict(cls, data):
        """Create from dictionary loaded from JSON."""
        # Create instance
        instance = cls(**data)
        
        # Process metadata to deserialize complex objects
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
            'memory_per_gpu': self.memory_per_gpu,
        }


def get_args_file_path(model, output_dir="generated_configs"):
    """Get the standard path for the args file."""
    return os.path.join(output_dir, model, "args.json")


def update_args_with_generation_metadata(model_name, result, output_dir="generated_configs"):
    """Update the args.json file with generation metadata."""
    args_file_path = get_args_file_path(model_name, output_dir)
    
    # Load existing args
    args = AutoTuneArgs.load_from_file(args_file_path)
    
    # Update with metadata and save
    args.save_with_metadata(args_file_path, result)
    
    return args_file_path


def update_args_with_performance_results(model_name, performance_dict, output_dir="generated_configs"):
    """Update the args.json file with performance results."""
    args_file_path = get_args_file_path(model_name, output_dir)
    
    # Load existing args
    args = AutoTuneArgs.load_from_file(args_file_path)
    
    # Update with performance results and save
    args.update_performance_results(performance_dict)
    args.save_to_file(args_file_path)
    
    return args_file_path


def _display_memory_analysis(memory_analysis):
    if not memory_analysis:
        console.print("[yellow]No memory analysis available[/yellow]")
        return
    
    console.print(f"\n[cyan] CUDA Memory Analysis & Run Status[/cyan]")
    table = Table(show_header=True, show_lines=True, title="Memory Usage Analysis & Execution Status")
    table.add_column("Configuration", style="cyan", width=40)  # Made wider since we removed config_str
    table.add_column("Memory Status", style="white", width=12)
    table.add_column("Run Status", style="white", width=12)
    table.add_column("Est. Usage (GB)", style="blue", width=15)
    table.add_column("GPU Memory (GB)", style="green", width=15)
    
    oom_count = 0
    safe_count = 0
    
    for config_name, analysis in memory_analysis.items():
        will_oom = analysis.get('will_oom', False)
        usage_gb = analysis.get('estimated_usage_gb', 0)
        total_gb = analysis.get('total_gpu_memory_gb', 0)
        config_values = analysis.get('config_values', {})
        
        if will_oom:
            memory_status = "[red]⚠ OOM Risk[/red]"
            run_status = "[red]Skip[/red]"
            oom_count += 1
        else:
            memory_status = "[green]Safe[/green]"
            run_status = "[green]▶ Run[/green]"
            safe_count += 1
        
        if config_name != "base_config" and all(v in [1, 512, 8192] for v in [
            config_values.get('tp', 1), config_values.get('mbs', 1), config_values.get('gbs', 512)
        ]):
            config_values = extract_all_values(config_name)
        
        table.add_row(
            config_name,
            memory_status,
            run_status,
            f"{usage_gb:.1f}",
            f"{total_gb:.0f}"
        )
    
    console.print(table)
    console.print(f"\n[cyan]Memory Analysis Summary:[/cyan]")
    console.print(f"Safe configurations (will run): {safe_count}")
    console.print(f"Potential OOM configurations (will be skipped): {oom_count}")
    
    if oom_count > 0:
        console.print(f"\n[yellow]⚠ Warning: {oom_count} configurations will be SKIPPED during 'lep autotune run'[/yellow]")
        console.print("[yellow]These configurations may cause CUDA OOM errors[/yellow]")
        console.print("[blue]To run them anyway: use 'lep autotune run --run-all'[/blue]")
        console.print("[blue] To fix: reduce micro batch sizes or increase parallelism[/blue]")
    
    console.print(table)
    console.print(f"\n[cyan] Memory Analysis Summary:[/cyan]")
    console.print(f" Safe configurations (will run): {safe_count}")
    console.print(f" Potential OOM configurations (will be skipped): {oom_count}")
    
    if oom_count > 0:
        console.print(f"\n[yellow]⚠ Warning: {oom_count} configurations will be SKIPPED during 'lep autotune run'[/yellow]")
        console.print("[yellow]These configurations may cause CUDA OOM errors[/yellow]")
        console.print("[blue] To run them anyway: use 'lep autotune run --run-all'[/blue]")
        console.print("[blue] To fix: reduce micro batch sizes or increase parallelism[/blue]")


def _display_configs_table(config_dir, model_name=None):
    """
    Display a table of configuration files with their details and status.
    
    Args:
        config_dir: Directory containing configuration files
        model_name: Model name (optional, will try to infer)
    """
    # Load args to get metadata
    try:
        if not model_name:
            # Try to infer model name from directory structure
            model_name = os.path.basename(config_dir)
        
        args_file_path = os.path.join(config_dir, "args.json")
        if os.path.exists(args_file_path):
            args = AutoTuneArgs.load_from_file(args_file_path)
            metadata = args.metadata
            has_metadata = bool(metadata)
        else:
            console.print(f"[yellow]No args.json found in {config_dir}[/yellow]")
            metadata = {}
            has_metadata = False
            args = None
            
    except Exception as e:
        console.print(f"[yellow]Could not load metadata: {e}[/yellow]")
        metadata = {}
        has_metadata = False
        args = None
    
    # Get configuration files (exclude args.json)
    all_files = os.listdir(config_dir)
    json_files = [f for f in all_files if f.endswith('.json') and f not in ['args.json']]
    
    if not json_files:
        console.print(f"[yellow]No configuration files found in: {config_dir}[/yellow]")
        return
    
    # Extract metadata info
    base_config_matches = metadata.get('base_config_matches', [])
    config_names = metadata.get('config_names', [])
    num_configs_generated = metadata.get('num_configs_generated', len(json_files) - 1)
    total_gpus = metadata.get('total_gpus', 'Unknown')
    generation_timestamp = metadata.get('generation_timestamp', 'Unknown')
    
    # Create table
    table = Table(show_header=True, show_lines=True, title=f"Configuration Files - {model_name or 'Unknown Model'}")
    table.add_column("Filename", style="cyan")
    table.add_column("Status", style="green")  
    table.add_column("Size", style="white")
    
    for filename in sorted(json_files):
        filepath = os.path.join(config_dir, filename)
        
        # Get file size
        try:
            stat = os.stat(filepath)
            size = f"{stat.st_size:,} bytes"
        except Exception as e:
            size = f"[red]Error: {e}[/red]"
        
        # Determine status
        if filename == "base_config.json":
            if base_config_matches:
                status = f"[yellow]Base Config (equivalent to: {', '.join(base_config_matches)})[/yellow]"
            else:
                status = "[bold green]Base Config[/bold green]"
        else:
            # Extract config name from filename (remove .json extension)
            config_name = filename.replace('.json', '')
            
            if has_metadata:
                if config_name in base_config_matches:
                    status = "[blue]Base Config Match[/blue]"
                elif config_name in config_names:
                    status = "[green]Generated[/green]"
                else:
                    status = "[dim]Unknown[/dim]"
            else:
                # No metadata available, just show as generated
                status = "[green]Generated[/green]"
        
        table.add_row(filename, status, size)
    
    console.print(table)
    
    # Display summary
    console.print(f"\n[cyan]📋 Summary:[/cyan]")
    if has_metadata:
        console.print(f"Model: {model_name}")
        console.print(f"Total GPUs: {total_gpus}")
        if args and hasattr(args, 'global_batch_sizes'):
            console.print(f"Global batch sizes: {args.global_batch_sizes}")
        if args and hasattr(args, 'resource_shape'):
            console.print(f"Resource shape: {args.resource_shape}")
        console.print(f"Generated configurations: {num_configs_generated}")
        console.print(f"Base config matches: {len(base_config_matches)}")
        console.print(f"Configuration files: {len(json_files)}")
        
        if generation_timestamp != 'Unknown':
            console.print(f"Generated: {generation_timestamp}")
        
        # Show memory analysis if available
        if args and args.has_memory_analysis():
            memory_analysis = args.get_memory_analysis()
            _display_memory_analysis(memory_analysis)
            
            # Add note about run behavior
            oom_configs = [name for name, analysis in memory_analysis.items() if analysis.get("will_oom", False)]
            if oom_configs:
                console.print(f"\n[yellow]Run Behavior Notes:[/yellow]")
                console.print(f"  • By default, 'lep autotune run' will SKIP the {len(oom_configs)} flagged configuration(s)")
                console.print(f"  • Use 'lep autotune run --run-all' to run ALL configurations including potential OOM ones")
                console.print(f"  • Use 'lep autotune check-memory' to see detailed memory breakdown")
        
        # Show performance results status
        if args and args.has_performance_results():
            results_timestamp = metadata.get('results_timestamp', 'Unknown')
            performance_dict = args.get_performance_dict()
            console.print(f"Performance Results: Available ({len(performance_dict)} configs)")
            if results_timestamp != 'Unknown':
                console.print(f"Results analyzed: {results_timestamp}")
            console.print("[green] Use 'lep autotune analyse-results' to analyze performance[/green]")
        else:
            console.print("[yellow]Performance Results: Not available[/yellow]")
            console.print("[yellow]Run 'lep autotune results' to generate performance data[/yellow]")
        
        if base_config_matches:
            console.print(f"\n[yellow]Note:[/yellow] Base config is equivalent to: {', '.join(base_config_matches)}")
            console.print("[yellow]These configurations will not be run separately during training.[/yellow]")
            
    else:
        console.print(f"Configuration files: {len(json_files)}")
        console.print("[yellow]No metadata available. Re-run 'lep autotune generate' for detailed status.[/yellow]")


def _analyze_performance_results_with_cost(performance_dict, args, total_steps, cost_per_gpu_hour):
    """Analyze and compare performance results with cost calculations."""
    if not performance_dict:
        console.print("[yellow]No performance data to analyze[/yellow]")
        return
    
    total_gpus = args.nodes * args.gpus_per_node
    
    # Calculate cost and time for each configuration
    config_analysis = {}
    for config_name, config_data in performance_dict.items():
        time_per_step = config_data.get('time_per_global_step', 0)
        m_tflops_gpu = config_data.get('m_tflops_gpu', 0)
        
        # Calculate total training time and cost
        total_training_time_seconds = time_per_step * total_steps
        total_training_time_hours = total_training_time_seconds / 3600
        total_cost = total_training_time_hours * cost_per_gpu_hour * total_gpus
        
        config_analysis[config_name] = {
            **config_data,
            'total_training_time_hours': total_training_time_hours,
            'total_training_time_days': total_training_time_hours / 24,
            'total_cost': total_cost,
            'cost_per_tflop': total_cost / (m_tflops_gpu * total_gpus) if m_tflops_gpu > 0 else float('inf')
        }
    
    # Sort configurations by m_tflops_gpu (descending - best first)
    sorted_configs = sorted(
        config_analysis.items(),
        key=lambda x: x[1].get('m_tflops_gpu', 0),
        reverse=True
    )
    
    best_config_name, best_config = sorted_configs[0]
    worst_config_name, worst_config = sorted_configs[-1]
    
    # Find base config (if exists)
    base_config_matches = args.metadata.get('base_config_matches', [])
    base_config_name = None
    base_config = None
    
    # Look for base config in performance results
    for config_name, config_data in config_analysis.items():
        if config_name in base_config_matches or config_name == 'base_config':
            base_config_name = config_name
            base_config = config_data
            break
    
    # Display analysis
    console.print("\n[cyan]💰 Performance & Cost Analysis Summary[/cyan]")
    console.print("=" * 80)
    
    # Best performing configuration
    console.print(f"\n[green]Best Performing Configuration: {best_config_name}[/green]")
    console.print(f"  M-TFLOPs/GPU: {best_config.get('m_tflops_gpu', 'N/A'):.2f}")
    console.print(f"  Time per Global Step: {best_config.get('time_per_global_step', 'N/A'):.4f}s")
    console.print(f"  Total Training Time: {best_config.get('total_training_time_days', 'N/A'):.1f} days")
    console.print(f"  Total Training Cost: ${best_config.get('total_cost', 'N/A'):,.2f}")
    console.print(f"  Cost per TFLOP: ${best_config.get('cost_per_tflop', 'N/A'):.2f}")
    
    # Base config comparison (if available)
    if base_config and base_config_name != best_config_name:
        console.print(f"\n[blue]Base Configuration: {base_config_name}[/blue]")
        console.print(f"  M-TFLOPs/GPU: {base_config.get('m_tflops_gpu', 'N/A'):.2f}")
        console.print(f"  Time per Global Step: {base_config.get('time_per_global_step', 'N/A'):.4f}s")
        console.print(f"  Total Training Time: {base_config.get('total_training_time_days', 'N/A'):.1f} days")
        console.print(f"  Total Training Cost: ${base_config.get('total_cost', 'N/A'):,.2f}")
        console.print(f"  Cost per TFLOP: ${base_config.get('cost_per_tflop', 'N/A'):.2f}")
        
        # Performance and cost comparison vs base
        tflops_improvement = ((best_config.get('m_tflops_gpu', 0) - base_config.get('m_tflops_gpu', 0)) / base_config.get('m_tflops_gpu', 1)) * 100
        time_savings = base_config.get('total_training_time_hours', 0) - best_config.get('total_training_time_hours', 0)
        cost_savings = base_config.get('total_cost', 0) - best_config.get('total_cost', 0)
        cost_savings_percent = (cost_savings / base_config.get('total_cost', 1)) * 100
        
        console.print(f"\n[yellow]Best vs Base Performance & Cost Savings:[/yellow]")
        console.print(f"  M-TFLOPs/GPU improvement: {tflops_improvement:+.1f}%")
        console.print(f"  Training time savings: {time_savings:.1f} hours ({time_savings/24:.1f} days)")
        console.print(f"  Cost savings: ${cost_savings:,.2f} ({cost_savings_percent:+.1f}%)")
        
        if cost_savings > 0:
            console.print(f"  [green] Total Savings: ${cost_savings:,.2f}[/green]")
        else:
            console.print(f"  [red] Additional Cost: ${abs(cost_savings):,.2f}[/red]")
    
    # Worst performing configuration
    if worst_config_name != best_config_name:
        console.print(f"\n[red]Worst Performing Configuration: {worst_config_name}[/red]")
        console.print(f"  M-TFLOPs/GPU: {worst_config.get('m_tflops_gpu', 'N/A'):.2f}")
        console.print(f"  Time per Global Step: {worst_config.get('time_per_global_step', 'N/A'):.4f}s")
        console.print(f"  Total Training Time: {worst_config.get('total_training_time_days', 'N/A'):.1f} days")
        console.print(f"  Total Training Cost: ${worst_config.get('total_cost', 'N/A'):,.2f}")
        console.print(f"  Cost per TFLOP: ${worst_config.get('cost_per_tflop', 'N/A'):.2f}")
        
        # Performance comparison best vs worst
        time_diff = worst_config.get('total_training_time_hours', 0) - best_config.get('total_training_time_hours', 0)
        cost_diff = worst_config.get('total_cost', 0) - best_config.get('total_cost', 0)
        tflops_diff = ((best_config.get('m_tflops_gpu', 0) - worst_config.get('m_tflops_gpu', 0)) / worst_config.get('m_tflops_gpu', 1)) * 100
        
        console.print(f"\n[yellow] Best vs Worst Performance & Cost Difference:[/yellow]")
        console.print(f"  M-TFLOPs/GPU difference: {tflops_diff:+.1f}%")
        console.print(f"  Training time difference: {time_diff:.1f} hours ({time_diff/24:.1f} days)")
        console.print(f"  Cost difference: ${cost_diff:,.2f}")
        console.print(f"  [red]Potential waste with worst config: ${cost_diff:,.2f}[/red]")
    
    # Create comprehensive performance & cost table
    console.print(f"\n[cyan] Top 5 Configurations - Performance & Cost Analysis[/cyan]")
    table = Table(show_header=True, show_lines=True, title="Performance & Cost Ranking")
    table.add_column("Rank", style="yellow", width=6)
    table.add_column("Configuration", style="cyan", width=20)
    table.add_column("M-TFLOPs/GPU", style="green", width=12)
    table.add_column("Training Days", style="blue", width=12)
    table.add_column("Total Cost", style="red", width=12)
    table.add_column("Status", style="white", width=15)
    
    for i, (config_name, config_data) in enumerate(sorted_configs[:5], 1):
        # Determine status
        status = "Generated"
        if config_name in base_config_matches or config_name == 'base_config':
            status = "Base Config"
        elif i == 1:
            status = " Best"
        
        table.add_row(
            str(i),
            config_name[:19],  # Truncate long names
            f"{config_data.get('m_tflops_gpu', 0):.2f}",
            f"{config_data.get('total_training_time_days', 0):.1f}",
            f"${config_data.get('total_cost', 0):,.0f}",
            status
        )
    
    console.print(table)
    
    # Cost efficiency analysis
    console.print(f"\n[cyan] Cost Efficiency Analysis[/cyan]")
    console.print("=" * 50)
    
    # Find most cost-efficient config (lowest cost per TFLOP)
    most_efficient = min(config_analysis.items(), key=lambda x: x[1].get('cost_per_tflop', float('inf')))
    most_efficient_name, most_efficient_data = most_efficient
    
    console.print(f"Most Cost-Efficient: {most_efficient_name}")
    console.print(f"  Cost per TFLOP: ${most_efficient_data.get('cost_per_tflop', 'N/A'):.2f}")
    console.print(f"  Total Cost: ${most_efficient_data.get('total_cost', 'N/A'):,.2f}")
    console.print(f"  M-TFLOPs/GPU: {most_efficient_data.get('m_tflops_gpu', 'N/A'):.2f}")
    
    # Recommendations
    console.print(f"\n[cyan] Recommendations[/cyan]")
    console.print("=" * 40)
    console.print(f"Best Performance: '{best_config_name}'")
    console.print(f"Most Cost-Efficient: '{most_efficient_name}'")
    
    if base_config:
        if base_config_name != best_config_name:
            savings = base_config.get('total_cost', 0) - best_config.get('total_cost', 0)
            console.print(f"Switch from base config to save: ${savings:,.2f}")
        else:
            console.print(f"Base config is already optimal!")
    
    console.print("\n[green]Cost analysis completed successfully![/green]")


def _analyze_performance_results_with_multiple_gbs(performance_dict, args, total_tokens, cost_per_gpu_hour):
    """Analyze performance results - SUPER SIMPLIFIED with ONE extraction function."""
    if not performance_dict:
        console.print("[yellow]No performance data to analyze[/yellow]")
        return
    
    total_gpus = args.nodes * args.gpus_per_node
    
    # Calculate cost and time for each configuration
    config_analysis = {}
    for config_name, config_data in performance_dict.items():
        time_per_step = config_data.get('time_per_global_step', 0)
        m_tflops_gpu = config_data.get('m_tflops_gpu', 0)
        
        # ONE FUNCTION CALL to get ALL values including GBS
        extracted_values = extract_all_values(config_name)
        gbs = extracted_values.get('gbs')
        if gbs is None or gbs == 512:  # 512 is default, might not be accurate
            gbs = args.global_batch_sizes[0] if args.global_batch_sizes else 512
            logger.warning(f"Could not extract GBS from {config_name}, using {gbs}")
        
        # Calculate tokens per step for this specific config
        tokens_per_step = args.seq_length * gbs
        total_steps = total_tokens / tokens_per_step
        
        # Calculate total training time and cost
        total_training_time_seconds = time_per_step * total_steps
        total_training_time_hours = total_training_time_seconds / 3600
        total_cost = total_training_time_hours * cost_per_gpu_hour * total_gpus
        
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
  
    _analyze_performance_results_with_cost(config_analysis, args, total_steps, cost_per_gpu_hour)


def _analyze_performance_results(performance_dict, args):
    """Analyze and compare performance results."""
    if not performance_dict:
        console.print("[yellow]No performance data to analyze[/yellow]")
        return
    
    # Sort configurations by m_tflops_gpu (descending - best first)
    sorted_configs = sorted(
        performance_dict.items(),
        key=lambda x: x[1].get('m_tflops_gpu', 0),
        reverse=True
    )
    
    best_config_name, best_config = sorted_configs[0]
    worst_config_name, worst_config = sorted_configs[-1]
    
    # Find base config (if exists)
    base_config_matches = args.metadata.get('base_config_matches', [])
    base_config_name = None
    base_config = None
    
    # Look for base config in performance results
    for config_name, config_data in performance_dict.items():
        if config_name in base_config_matches or config_name == 'base_config':
            base_config_name = config_name
            base_config = config_data
            break
    
    # Display analysis
    console.print("\n[cyan] Performance Analysis Summary[/cyan]")
    console.print("=" * 60)
    
    # Best performing configuration
    console.print(f"\n[green] Best Performing Configuration: {best_config_name}[/green]")
    console.print(f"  M-TFLOPs/GPU: {best_config.get('m_tflops_gpu', 'N/A'):.2f}")
    console.print(f"  Time per Global Step: {best_config.get('time_per_global_step', 'N/A'):.4f}s")
    console.print(f"  Samples/s: {best_config.get('samples_per_s', 'N/A'):.2f}")
    console.print(f"  Total M-TFLOPs: {best_config.get('m_tflops', 'N/A'):.2f}")
    
    # Base config comparison (if available)
    if base_config and base_config_name != best_config_name:
        console.print(f"\n[blue] Base Configuration: {base_config_name}[/blue]")
        console.print(f"  M-TFLOPs/GPU: {base_config.get('m_tflops_gpu', 'N/A'):.2f}")
        console.print(f"  Time per Global Step: {base_config.get('time_per_global_step', 'N/A'):.4f}s")
        console.print(f"  Samples/s: {base_config.get('samples_per_s', 'N/A'):.2f}")
        console.print(f"  Total M-TFLOPs: {base_config.get('m_tflops', 'N/A'):.2f}")
        
        # Performance comparison vs base
        tflops_improvement = ((best_config.get('m_tflops_gpu', 0) - base_config.get('m_tflops_gpu', 0)) / base_config.get('m_tflops_gpu', 1)) * 100
        time_improvement = ((base_config.get('time_per_global_step', 1) - best_config.get('time_per_global_step', 1)) / base_config.get('time_per_global_step', 1)) * 100
        
        console.print(f"\n[yellow]⚡ Best vs Base Performance:[/yellow]")
        console.print(f"  M-TFLOPs/GPU improvement: {tflops_improvement:+.1f}%")
        console.print(f"  Time per step improvement: {time_improvement:+.1f}%")
    
    # Worst performing configuration
    if worst_config_name != best_config_name:
        console.print(f"\n[red]🐌 Worst Performing Configuration: {worst_config_name}[/red]")
        console.print(f"  M-TFLOPs/GPU: {worst_config.get('m_tflops_gpu', 'N/A'):.2f}")
        console.print(f"  Time per Global Step: {worst_config.get('time_per_global_step', 'N/A'):.4f}s")
        console.print(f"  Samples/s: {worst_config.get('samples_per_s', 'N/A'):.2f}")
        console.print(f"  Total M-TFLOPs: {worst_config.get('m_tflops', 'N/A'):.2f}")
        
        # Performance comparison best vs worst
        tflops_diff = ((best_config.get('m_tflops_gpu', 0) - worst_config.get('m_tflops_gpu', 0)) / worst_config.get('m_tflops_gpu', 1)) * 100
        time_diff = ((worst_config.get('time_per_global_step', 1) - best_config.get('time_per_global_step', 1)) / worst_config.get('time_per_global_step', 1)) * 100
        
        console.print(f"\n[yellow] Best vs Worst Performance:[/yellow]")
        console.print(f"  M-TFLOPs/GPU difference: {tflops_diff:+.1f}%")
        console.print(f"  Time per step difference: {time_diff:+.1f}%")
    
    # Create performance table
    console.print(f"\n[cyan] Top 5 Configurations by M-TFLOPs/GPU[/cyan]")
    table = Table(show_header=True, show_lines=True, title="Performance Ranking")
    table.add_column("Rank", style="yellow", width=6)
    table.add_column("Configuration", style="cyan", width=20)
    table.add_column("M-TFLOPs/GPU", style="green", width=12)
    table.add_column("Time/Step (s)", style="blue", width=12)
    table.add_column("Status", style="white", width=15)
    
    for i, (config_name, config_data) in enumerate(sorted_configs[:5], 1):
        # Determine status
        status = "Generated"
        if config_name in base_config_matches or config_name == 'base_config':
            status = "Base Config"
        elif i == 1:
            status = " Best"
        
        table.add_row(
            str(i),
            config_name,
            f"{config_data.get('m_tflops_gpu', 0):.2f}",
            f"{config_data.get('time_per_global_step', 0):.4f}",
            status
        )
    
    console.print(table)
    
    # Recommendations
    console.print(f"\n[cyan] Recommendations[/cyan]")
    console.print("=" * 40)
    console.print(f" Use configuration '{best_config_name}' for optimal performance")
    if base_config and base_config_name != best_config_name:
        console.print(f" Consider switching from base config '{base_config_name}'")
    console.print(f" Performance range: {worst_config.get('m_tflops_gpu', 0):.1f} - {best_config.get('m_tflops_gpu', 0):.1f} M-TFLOPs/GPU")
    
    console.print("\n[green]Analysis completed successfully![/green]")


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


def validate_parallelism_sizes(ctx, param, value):
    """Validate parallelism size inputs."""
    if value == "auto":
        return value
    
    if isinstance(value, (list, tuple)):
        return list(value)
    
    if isinstance(value, str):
        if value.strip().lower() == "auto":
            return "auto"
        try:
            return [int(x.strip()) for x in value.split(",")]
        except ValueError:
            raise click.BadParameter(f"Invalid value: {value}. Use 'auto' or comma-separated integers.")
    
    return value


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


@autotune.command()
@click.option("--model", "-m", type=str, default="nemotron3_4b", callback=validate_model_callback, help="Model to pretrain.")
@click.option("--nodes", "-n", type=int, default=1, callback=validate_positive_int, help="Number of nodes for training.")
@click.option("--gpus-per-node", "--gpus_per_node", "gpus_per_node", type=int, default=8, callback=validate_positive_int, help="GPUs per node.")
@click.option("--tensor-parallel-sizes", "--tensor_parallel_sizes", "tensor_parallel_sizes", type=int, multiple=True, default=[1, 2], help="Tensor parallel sizes to test.")
@click.option("--virtual-pipeline-model-parallel-sizes", "--virtual_pipeline_model_parallel_sizes", "virtual_pipeline_model_parallel_size", type=int, multiple=True, default=None, help="virtual Pipline Model parallel sizes to test.")
@click.option("--pipeline-parallel-sizes", "--pipeline_parallel_sizes", "pipeline_parallel_sizes", type=int, multiple=True, default=[1, 2], callback=validate_parallelism_sizes, help="Pipeline parallel sizes.")
@click.option("--context-parallel-sizes", "--context_parallel_sizes", "context_parallel_sizes", type=int, multiple=True, default=[1, 2], help="Context parallel sizes to test.")
@click.option("--micro-batch-sizes", "--micro_batch_sizes", "micro_batch_sizes", type=int, default=[1, 2, 4], multiple=True, callback=validate_parallelism_sizes, help="Micro batch sizes.")
@click.option("--max-model-parallel-size", "--max_model_parallel_size", "max_model_parallel_size", type=int, default=32, callback=validate_positive_int, help="Maximum model parallel size.")
@click.option("--min-model-parallel-size", "--min_model_parallel_size", "min_model_parallel_size", type=int, default=1, callback=validate_positive_int, help="Minimum model parallel size.")
@click.option("--max-steps-per-run", "--max_steps_per_run", "max_steps_per_run", type=int, default=10, callback=validate_positive_int, help="Maximum steps per run for testing.")
@click.option("--max-minutes-per-run", "--max_minutes_per_run", "max_minutes_per_run", type=int, default=10, callback=validate_positive_int, help="Maximum minutes per run for testing.")
@click.option("--num-tokens-in-b", "--run_pretraining_only", "num_tokens_in_b", type=int, default=1000, callback=validate_positive_int, help="Number of tokens in billions.")
@click.option("--vocab-size", "--vocab_size", "vocab_size", type=int, default=32000, callback=validate_positive_int, help="Vocabulary size.")
@click.option("--seq-length", "--seq_length", "seq_length", type=int, default=8192, callback=validate_positive_int, help="Sequence length for the model.")
@click.option("--global-batch-sizes", "--global_batch_sizes", "global_batch_sizes", type=int, multiple=True, default=[512], help="Global batch sizes to test.")
@click.option("--val-check-interval", "--val_check_interval", "val_check_interval", type=int, default=50, callback=validate_positive_int, help="Validation check interval.")
@click.option("--max-steps", "--max_steps", "max_steps", type=int, default=10, callback=validate_positive_int, help="Maximum training steps.")
@click.option("--output-dir", "--output_dir", "output_dir", type=str, default="generated_configs", help="Directory to save generated configurations.")
# New dynamic executor options
@click.option("--resource-shape", "--resource_shape", "resource_shape", type=str, default="gpu.8xh200", help="GPU resource shape (e.g., gpu.8xh200, gpu.4xh100).")
@click.option("--container-image", "--container_image", "container_image", type=str, default="nvcr.io/nvidia/nemo:25.02", help="Docker container image to use.")
@click.option("--nemo-run-dir", "--nemo_run_dir", "nemo_run_dir", type=str, default="/nemo-workspace/nemo-run", help="Directory for nemo-run.")
@click.option("--mount-path", "--mount_path", "mount_path", type=str, default="/nemo-workspace", help="Mount path in container.")
@click.option("--mount-from", "--mount_from", "mount_from", type=str, default="node-nfs:shared", help="Mount source.")
@click.option("--node-group", "--node_group", "node_group", type=str, default="nebius-h200-01", help="Node group for execution.")
@click.option("--hf-token", "--hf_token", "hf_token", type=str, default=None, help="HuggingFace token (optional).")
@click.option("--wandb-api-key", "--wandb_api_key", "wandb_api_key", type=str, default=None, help="Weights & Biases API key (optional).")
@click.option("--torch-home", "--torch_home", "torch_home", type=str, default="/nemo-workspace/.cache", help="PyTorch cache directory.")
@click.option("--pythonpath", type=str, default="/nemo-workspace/nemo-run:$PYTHONPATH", help="Python path configuration.")
@click.option("--memory-per-gpu", "--memory_per_gpu", "memory_per_gpu", type=float, default=None, help="Custom GPU memory in GB (overrides auto-detection from resource-shape).")
def generate(**kwargs):
    """Generate AutoTune configurations for NeMo pretraining - OPTIMIZED VERSION."""
    console.print(f"Generating AutoTune configurations for model: [bold]{kwargs['model']}[/bold]")
    
    # ONE FUNCTION CALL to get all info: GPU specs, model size, etc.
    gpu_type, gpu_count, gpu_memory_gb = extract_gpu_specs(kwargs['resource_shape'], kwargs.get('memory_per_gpu'))
    model_info = extract_all_values(kwargs['model'])
    model_size_b = model_info.get('model_size_b')
    
    console.print(f" Resource: [blue]{kwargs['resource_shape']}[/blue] ({gpu_type.upper()}, {gpu_memory_gb}GB per GPU)")
    if model_size_b:
        console.print(f" Model: [cyan]{kwargs['model']}[/cyan] ({model_size_b}B parameters)")
    else:
        console.print(f" Model: [cyan]{kwargs['model']}[/cyan]")
    
    # Create args object
    args = AutoTuneArgs(**kwargs)
    
    try:
        # Validate all configurations before proceeding
        console.print("[yellow]Validating configuration parameters...[/yellow]")
        is_valid, error_msg = validate_all_configs(args)
        if not is_valid:
            console.print("[red]Configuration validation failed:[/red]")
            console.print(f"   {error_msg}")
            sys.exit(1)
        
        console.print("[green]Configuration validation passed![/green]")
        
        # Save args to file first (without metadata)
        args_file_path = get_args_file_path(args.model, kwargs['output_dir'])
        args.save_to_file(args_file_path)
        console.print(f"[blue]Arguments saved to: {args_file_path}[/blue]")
        
        # Generate configurations
        console.print("[yellow]Generating configurations...[/yellow]")

        result = generate_recipe_configs(args)
    
        # Update args.json with generation metadata (including serialized objects)
        update_args_with_generation_metadata(args.model, result, kwargs['output_dir'])
        console.print(f"[blue]Metadata and objects saved to: {args_file_path}[/blue]")
        
        console.print("[green]Configurations generated successfully![/green]")
        console.print(f"Saved to: {os.path.join(kwargs['output_dir'], args.model)}")
        console.print(f"Generated {result['num_configs_generated']} configurations")
        
        # Show memory analysis summary
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
        
        # Display configuration summary using the new function
        model_config_dir = os.path.join(kwargs['output_dir'], args.model)
        # _display_configs_table(model_config_dir, args.model)
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error generating configurations: {e}[/red]")
        logger.error(f"Configuration generation failed: {e}")
        sys.exit(1)


@autotune.command()
@click.option("--config-dir", "--config_dir", "config_dir", type=str, default="generated_configs", help="Directory containing generated configurations.")
@click.option("--model", "-m", type=str, help="Model name (will be inferred if not provided).")
@click.option("--sequential", is_flag=True, default=False, help="Run configurations sequentially instead of in parallel.")
@click.option("--run-all", "--run_all", "run_all", is_flag=True, default=False, help="Run all configurations including those with potential CUDA OOM risk.")
def run(config_dir, model, sequential, run_all):
    """Run AutoTune pretraining with generated configurations."""
    
    try:
        # Load args from file
        args = _load_args_from_config_dir(config_dir, model)
        args.sequential = sequential  # Override with CLI flag
        
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
        
        # Generate configurations and run pretraining
        config_result = generate_recipe_configs(args)
        
        # Get memory analysis for filtering
        memory_analysis = config_result.get('memory_analysis', {})
        
        # Show memory analysis summary before running
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
@click.option("--path", "-p", type=str, required=True, help="Path to AutoConfigurator logs directory.")
@click.option("--output-file", "--output_file", "output_file", type=str, help="Specific file path to save results (optional).")
@click.option("--top-n", "--top_n", "top_n", type=int, default=10, callback=validate_positive_int, help="Number of top configurations to display.")
@click.option("--log-prefix", "--log_prefix", "log_prefix", type=str, required=True, help="Log file prefix for result files.")
@click.option("--config-dir", "--config_dir", "config_dir", type=str, default="generated_configs", help="Directory containing generated configurations.")
@click.option("--model", "-m", type=str, help="Model name (will be inferred if not provided).")
@click.option("--force-reconstruct", is_flag=True, default=False, help="Force reconstruction instead of using saved objects.")
def results(path, output_file, top_n, log_prefix, config_dir, model, force_reconstruct):
    """Collect and display AutoConfigurator results."""
    console.print(f"Collecting AutoTune results from: [bold]{path}[/bold]")
    
    try:
        # Check if logs directory exists
        if not os.path.exists(path):
            console.print(f"[red]Logs directory not found: {path}[/red]")
            console.print("[yellow]Tip: Run 'lep autotune run' first to generate training logs[/yellow]")
            sys.exit(1)
        
        # Load args from file
        args = _load_args_from_config_dir(config_dir, model)
        
        console.print(f"[blue]Loaded configuration for model: {args.model}[/blue]")
        console.print(f"  Resources: {args.nodes} nodes × {args.gpus_per_node} GPUs = {args.nodes * args.gpus_per_node} total GPUs")
        console.print(f"Resource shape: {args.resource_shape}")
        console.print(f"  Batch sizes: micro={args.micro_batch_sizes}, global={args.global_batch_sizes}")
        console.print(f"  Sequence length: {args.seq_length}")
        console.print(f"  Training: max_steps={args.max_steps}, val_check_interval={args.val_check_interval}")
        
        # Try to use saved objects first, fallback to reconstruction
        if not force_reconstruct and args.has_valid_objects():
            console.print("[blue]Using saved AutoConfigurator objects from args.json[/blue]")
            base_config = args.get_base_config()
            runner = args.get_runner()
            metadata = args.metadata
        else:
            if force_reconstruct:
                console.print("[yellow]Force reconstruction requested - reconstructing AutoConfigurator configuration...[/yellow]")
            else:
                console.print("[yellow]Saved objects not available - reconstructing AutoConfigurator configuration...[/yellow]")
            
            config_result = generate_recipe_configs(args)
            base_config = config_result['base_config']
            runner = config_result['runner']
            metadata = args.metadata

        # Call the improved get_results function with output file handling
        console.print("[yellow]Analyzing training results...[/yellow]")

        performance_dict = get_results_with_output(
            base_config=base_config,
            runner=runner,
            path_to_logs=path,
            log_file_prefix=log_prefix,
            num_configs_generated=metadata.get('num_configs_generated'),   
            base_config_matches=metadata.get('base_config_matches', []),       
            output_file=output_file,
            output_top_n=top_n
        )
        
        # Save performance results to args.json
        if performance_dict:
            console.print("[blue]Saving performance results to args.json...[/blue]")
            update_args_with_performance_results(args.model, performance_dict, config_dir)
            console.print("[blue]Performance results saved![/blue]")
        
        console.print(f"[green]Results analysis completed successfully![/green]")
        if output_file:
            console.print(f"[green]Results saved to: {output_file}[/green]")
        else:
            console.print(f"[green]Results displayed in terminal[/green]")
        console.print(f"[green]Analyzed top {metadata.get('num_configs_generated', 'Unknown')} configurations[/green]")
        
    except Exception as e:
        console.print(f"[red]Error during results analysis: {e}[/red]")
        logger.error(f"Results analysis failed: {e}")
        sys.exit(1)


@autotune.command(name="analyse-results")
@click.option("--config-dir", "--config_dir", "config_dir", type=str, default="generated_configs", help="Directory containing generated configurations.")
@click.option("--model", "-m", type=str, help="Model name (will be inferred if not provided).")
@click.option("--cost-per-gpu-hour", "--cost_per_gpu_hour", "cost_per_gpu_hour", type=float, default=4.0, callback=validate_positive_float, help="Cost per GPU hour in USD (default: $4.0 for H100).")
def analyse_results(config_dir, model, cost_per_gpu_hour):
    """Analyze AutoTune performance results and compare configurations with cost analysis."""
    console.print(f"Analyzing AutoTune performance results with cost analysis...")
    
    try:
        # Load args from file
        args = _load_args_from_config_dir(config_dir, model)
        
        console.print(f"[blue]Loaded configuration for model: {args.model}[/blue]")
        
        # Check if performance results exist
        if not args.has_performance_results():
            console.print("[yellow]No performance results found in args.json[/yellow]")
            console.print("[yellow]Please run 'lep autotune results' first to generate performance data[/yellow]")
            console.print(f"[yellow]Example: lep autotune results --path /path/to/logs --log-prefix nemo[/yellow]")
            sys.exit(1)
        
        performance_dict = args.get_performance_dict()
        console.print(f"[green]Found performance results for {len(performance_dict)} configurations[/green]")
        
        # Display training parameters for cost calculation
        total_tokens = args.num_tokens_in_b * 1_000_000_000  # Convert billions to actual tokens

        # For cost analysis, we need to extract GBS from individual config names
        # since different configs may have different GBS values
        console.print(f"\n[cyan] Training Configuration for Cost Analysis[/cyan]")
        console.print(f"  Total tokens to train: {total_tokens:,} ({args.num_tokens_in_b}B)")
        console.print(f"  Sequence length: {args.seq_length:,}")
        console.print(f"  Global batch sizes tested: {args.global_batch_sizes}")
        console.print(f"  Total GPUs: {args.nodes * args.gpus_per_node}")
        console.print(f"Resource shape: {args.resource_shape}")
        console.print(f"  Cost per GPU hour: ${cost_per_gpu_hour:.2f}")
        
        # For each config, extract GBS from config name and calculate cost
        _analyze_performance_results_with_multiple_gbs(performance_dict, args, total_tokens, cost_per_gpu_hour)
        
    except Exception as e:
        console.print(f"[red]Error analyzing results: {e}[/red]")
        logger.error(f"Results analysis failed: {e}")
        sys.exit(1)


@autotune.command()
@click.option("--config-dir", "--config_dir", "config_dir", type=str, default="generated_configs", help="Directory containing generated configurations.")
@click.option("--model", "-m", type=str, help="Model name (will be inferred if not provided).")
def list_configs(config_dir, model):
    """List generated AutoTune configurations with detailed status."""
    try:
        args = _load_args_from_config_dir(config_dir, model)
        model_config_dir = os.path.join(config_dir, args.model)
        
        console.print(f"Configurations for model: [bold]{args.model}[/bold]")
        console.print(f"Location: {model_config_dir}")
        
        # Display configurations using the updated function
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


@autotune.command(name="check-memory")
@click.option("--config-dir", "--config_dir", "config_dir", type=str, default="generated_configs", help="Directory containing generated configurations.")
@click.option("--model", "-m", type=str, help="Model name (will be inferred if not provided).")
@click.option("--safety-margin", "--safety_margin", "safety_margin", type=float, default=5.0, callback=validate_positive_float, help="Safety margin in GB to leave unused (default: 5.0).")
def check_memory(config_dir, model, safety_margin):
    """Check CUDA memory usage for all generated configurations - OPTIMIZED VERSION."""
    console.print(f" Analyzing CUDA memory usage for configurations...")
    
    try:
        args = _load_args_from_config_dir(config_dir, model)
        
        # ONE FUNCTION CALL to get all info: GPU specs, model size, etc.
        gpu_type, gpu_count, gpu_memory_gb = extract_gpu_specs(args.resource_shape, getattr(args, 'memory_per_gpu', None))
        model_info = extract_all_values(args.model)
        model_size_b = model_info.get('model_size_b')
        
        console.print(f"[blue] Configuration Summary:[/blue]")
        console.print(f"  Model: [cyan]{args.model}[/cyan] ({model_size_b}B parameters)" if model_size_b else f"  Model: [cyan]{args.model}[/cyan]")
        console.print(f"  Resource: [blue]{args.resource_shape}[/blue] ({gpu_type.upper()}, {gpu_memory_gb}GB per GPU)")
        console.print(f"  Safety margin: [yellow]{safety_margin:.1f} GB[/yellow]")
        
        if args.has_memory_analysis():
            console.print("[green] Using existing memory analysis from generation[/green]")
            memory_analysis = args.get_memory_analysis()
        else:
            console.print("[yellow]⚙ No existing memory analysis found. Performing fresh analysis...[/yellow]")
            
            result = generate_recipe_configs(args)
            memory_analysis = result.get('memory_analysis', {})
            
            if not memory_analysis:
                console.print("[red] Failed to generate memory analysis[/red]")
                sys.exit(1)
        
        _display_memory_analysis(memory_analysis)
        
        oom_configs = [name for name, analysis in memory_analysis.items() if analysis.get("will_oom", False)]
        safe_configs = [name for name, analysis in memory_analysis.items() if not analysis.get("will_oom", False)]
        
        console.print(f"\n[cyan]🎯 Recommendations:[/cyan]")
        if safe_configs:
            console.print(f" Safe configurations to use: {len(safe_configs)}")
            console.print(f"  Examples: {', '.join(safe_configs[:3])}{'...' if len(safe_configs) > 3 else ''}")
        
        if oom_configs:
            console.print(f"⚠ Configurations to avoid: {len(oom_configs)}")
            console.print(f"  These may cause CUDA OOM: {', '.join(oom_configs[:3])}{'...' if len(oom_configs) > 3 else ''}")
            console.print("[yellow] Consider reducing micro batch sizes or adjusting parallelism settings[/yellow]")
        
        console.print("\n[green] Memory analysis completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red] Error analyzing memory: {e}[/red]")
        logger.error(f"Memory analysis failed: {e}")
        sys.exit(1)


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
    
    # Load args from file
    args_file_path = get_args_file_path(model, config_dir)
    if not os.path.exists(args_file_path):
        console.print(f"[red]Arguments file not found: {args_file_path}[/red]")
        console.print("[yellow]Tip: Run 'lep autotune generate' first to create configurations[/yellow]")
        sys.exit(1)
    
    return AutoTuneArgs.load_from_file(args_file_path)


def add_command(cli_group):
    """Add the autotune command group to the main CLI."""
    cli_group.add_command(autotune)
