"""
AutoTune utility functions for validation and configuration comparison.

This module contains helper functions for:
- Model validation
- Configuration parameter validation
- Configuration comparison and matching
- Configuration value extraction and parsing
"""

import os
import json
import re
import logging
from typing import Dict, Any, Union, List, Tuple, Optional
from nemo.collections import llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ========== MODEL VALIDATION FUNCTIONS ==========

def get_supported_models() -> List[str]:
    """
    Get list of supported models from NeMo's llm module.
    Returns a list of model names that have pretrain_recipe methods.
    """
    supported_models = []
    
    try:
        # Get all attributes from llm module that have pretrain_recipe
        for attr_name in dir(llm):
            if not attr_name.startswith("_"):
                attr = getattr(llm, attr_name)
                if hasattr(attr, "pretrain_recipe"):
                    supported_models.append(attr_name)
    except Exception as e:
        logger.warning(f"Error getting supported models: {e}")
    
    return sorted(supported_models)

def validate_model_support(model_name: str) -> Tuple[bool, str]:
    """
    Validate if a model is supported by NeMo.
    
    Args:
        model_name: Name of the model to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        supported_models = get_supported_models()
        
        if model_name in supported_models:
            return True, ""
        
        # Create helpful error message
        error_msg = (
            f"Model '{model_name}' is not supported.\n"
            f"Supported models: {', '.join(supported_models)}\n"
            f"For the latest list of supported models, please check: "
            f"https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py"
        )
        
        return False, error_msg
        
    except Exception as e:
        error_msg = (
            f"Error validating model '{model_name}': {e}\n"
            f"Please check: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py"
        )
        return False, error_msg

# ========== CONFIGURATION VALIDATION FUNCTIONS ==========

def validate_parallelism_settings(
    tensor_parallel_sizes: List[int],
    pipeline_parallel_sizes: Union[str, List[int]],
    context_parallel_sizes: List[int],
    nodes: int,
    gpus_per_node: int
) -> Tuple[bool, str]:
    """
    Validate parallelism settings for consistency.
    
    Args:
        tensor_parallel_sizes: List of TP sizes
        pipeline_parallel_sizes: PP sizes (can be "auto" or list)
        context_parallel_sizes: List of CP sizes
        nodes: Number of nodes
        gpus_per_node: GPUs per node
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    total_gpus = nodes * gpus_per_node
    
    # Validate tensor parallel sizes
    for tp in tensor_parallel_sizes:
        if tp <= 0:
            return False, f"Tensor parallel size must be positive, got: {tp}"
        if total_gpus % tp != 0:
            return False, f"Tensor parallel size {tp} must divide total GPUs {total_gpus}"
    
    # Validate pipeline parallel sizes if not auto
    if isinstance(pipeline_parallel_sizes, list):
        for pp in pipeline_parallel_sizes:
            if pp <= 0:
                return False, f"Pipeline parallel size must be positive, got: {pp}"
            if total_gpus % pp != 0:
                return False, f"Pipeline parallel size {pp} must divide total GPUs {total_gpus}"
    
    # Validate context parallel sizes
    for cp in context_parallel_sizes:
        if cp <= 0:
            return False, f"Context parallel size must be positive, got: {cp}"
        if total_gpus % cp != 0:
            return False, f"Context parallel size {cp} must divide total GPUs {total_gpus}"
    
    return True, ""

def validate_resource_settings(
    nodes: int,
    gpus_per_node: int,
    max_model_parallel_size: int,
    min_model_parallel_size: int
) -> Tuple[bool, str]:
    """
    Validate resource settings.
    
    Args:
        nodes: Number of nodes
        gpus_per_node: GPUs per node
        max_model_parallel_size: Maximum model parallel size
        min_model_parallel_size: Minimum model parallel size
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if nodes <= 0:
        return False, f"Number of nodes must be positive, got: {nodes}"
    
    if gpus_per_node <= 0:
        return False, f"GPUs per node must be positive, got: {gpus_per_node}"
    
    if min_model_parallel_size <= 0:
        return False, f"Minimum model parallel size must be positive, got: {min_model_parallel_size}"
    
    if max_model_parallel_size <= 0:
        return False, f"Maximum model parallel size must be positive, got: {max_model_parallel_size}"
    
    if min_model_parallel_size > max_model_parallel_size:
        return False, f"Minimum model parallel size ({min_model_parallel_size}) cannot be greater than maximum ({max_model_parallel_size})"
    
    total_gpus = nodes * gpus_per_node
    if max_model_parallel_size > total_gpus:
        return False, f"Maximum model parallel size ({max_model_parallel_size}) cannot exceed total GPUs ({total_gpus})"
    
    return True, ""

def validate_training_settings(
    max_steps_per_run: int,
    max_minutes_per_run: int,
    num_tokens_in_b: int,
    vocab_size: int,
    seq_length: int = None,
    global_batch_sizes: Union[List[int], Tuple[int, ...]] = None,
    max_steps: int = None
) -> Tuple[bool, str]:
    """
    Validate training settings.
    
    Args:
        max_steps_per_run: Maximum steps per run
        max_minutes_per_run: Maximum minutes per run
        num_tokens_in_b: Number of tokens in billions
        vocab_size: Vocabulary size
        seq_length: Sequence length (optional)
        global_batch_sizes: List of global batch sizes (optional)
        max_steps: Maximum training steps (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if max_steps_per_run <= 0:
        return False, f"Maximum steps per run must be positive, got: {max_steps_per_run}"
    
    if max_minutes_per_run <= 0:
        return False, f"Maximum minutes per run must be positive, got: {max_minutes_per_run}"
    
    if num_tokens_in_b <= 0:
        return False, f"Number of tokens in billions must be positive, got: {num_tokens_in_b}"
    
    if vocab_size <= 0:
        return False, f"Vocabulary size must be positive, got: {vocab_size}"
    
    if seq_length is not None and seq_length <= 0:
        return False, f"Sequence length must be positive, got: {seq_length}"
    
    if global_batch_sizes is not None:
        if not isinstance(global_batch_sizes, (list, tuple)):
            return False, f"Global batch sizes must be a list or tuple, got: {type(global_batch_sizes)}"
        
        if len(global_batch_sizes) == 0:
            return False, f"Global batch sizes list cannot be empty"
        
        for gbs in global_batch_sizes:
            if not isinstance(gbs, int) or gbs <= 0:
                return False, f"Each global batch size must be a positive integer, got: {gbs}"
    
    if max_steps is not None and max_steps <= 0:
        return False, f"Maximum steps must be positive, got: {max_steps}"
    
    return True, ""

def validate_all_configs(args) -> Tuple[bool, str]:
    """
    Validate all configuration parameters.
    
    Args:
        args: Arguments object with all configuration parameters
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate model support
    is_valid, error_msg = validate_model_support(args.model)
    if not is_valid:
        return False, error_msg
    
    # Validate resource settings
    is_valid, error_msg = validate_resource_settings(
        args.nodes,
        args.gpus_per_node,
        args.max_model_parallel_size,
        args.min_model_parallel_size
    )
    if not is_valid:
        return False, error_msg
    
    # Validate parallelism settings
    is_valid, error_msg = validate_parallelism_settings(
        args.tensor_parallel_sizes,
        args.pipeline_parallel_sizes,
        args.context_parallel_sizes,
        args.nodes,
        args.gpus_per_node
    )
    if not is_valid:
        return False, error_msg
    
    # Validate training settings
    training_kwargs = {
        'max_steps_per_run': args.max_steps_per_run,
        'max_minutes_per_run': args.max_minutes_per_run,
        'num_tokens_in_b': args.num_tokens_in_b,
        'vocab_size': args.vocab_size,
        'global_batch_sizes': args.global_batch_sizes
    }
    
    # Add optional parameters if they exist
    if hasattr(args, 'seq_length'):
        training_kwargs['seq_length'] = args.seq_length
    if hasattr(args, 'global_batch_sizes'):
        training_kwargs['global_batch_sizes'] = args.global_batch_sizes
    if hasattr(args, 'max_steps'):
        training_kwargs['max_steps'] = args.max_steps
    
    is_valid, error_msg = validate_training_settings(**training_kwargs)
    if not is_valid:
        return False, error_msg
    
    return True, ""

# ========== CONFIGURATION PARSING FUNCTIONS ==========

def extract_data_params(data_str: str) -> Dict[str, Any]:
    """
    Extract data parameters from the data string using regex patterns.
    """
    params = {}
    
    # Remove the outer wrapper if present
    data_str = data_str.strip()
    if data_str.startswith('"<Config[MockDataModule(') and data_str.endswith(')]>"'):
        data_str = data_str[1:-1]  # Remove quotes
    if data_str.startswith('<Config[MockDataModule(') and data_str.endswith(')]>'):
        data_str = data_str[24:-3]  # Remove wrapper
    
    # Extract data parameters
    data_patterns = {
        'seq_length': r'seq_length=(\d+)',
        'micro_batch_size': r'micro_batch_size=(\d+)',
        'global_batch_size': r'global_batch_size=(\d+)'
    }
    
    for param, pattern in data_patterns.items():
        match = re.search(pattern, data_str)
        if match:
            params[param] = int(match.group(1))
    
    return params

def extract_trainer_params(trainer_str: str) -> Dict[str, Any]:
    """
    Extract trainer parameters from the trainer string using regex patterns.
    This approach is more reliable for the specific format we're dealing with.
    """
    params = {}
    
    # Remove the outer wrapper
    trainer_str = trainer_str.strip()
    if trainer_str.startswith('"<Config[Trainer(') and trainer_str.endswith(')]>"'):
        trainer_str = trainer_str[1:-1]  # Remove quotes
    if trainer_str.startswith('<Config[Trainer(') and trainer_str.endswith(')]>'):
        trainer_str = trainer_str[16:-3]  # Remove wrapper
    
    # Extract simple parameters
    simple_patterns = {
        'accelerator': r"accelerator='([^']+)'",
        'devices': r'devices=(\d+)',
        'num_nodes': r'num_nodes=(\d+)',
        'max_steps': r'max_steps=(\d+)',
        'limit_val_batches': r'limit_val_batches=(\d+)',
        'limit_test_batches': r'limit_test_batches=(\d+)',
        'val_check_interval': r'val_check_interval=(\d+)',
        'log_every_n_steps': r'log_every_n_steps=(\d+)',
        'accumulate_grad_batches': r'accumulate_grad_batches=(\d+)',
        'use_distributed_sampler': r'use_distributed_sampler=(True|False)'
    }
    
    for param, pattern in simple_patterns.items():
        match = re.search(pattern, trainer_str)
        if match:
            value = match.group(1)
            if param in ['devices', 'num_nodes', 'max_steps', 'limit_val_batches', 
                        'limit_test_batches', 'val_check_interval', 'log_every_n_steps', 
                        'accumulate_grad_batches']:
                params[param] = int(value)
            elif param == 'use_distributed_sampler':
                params[param] = value == 'True'
            else:
                params[param] = value
    
    # Extract strategy parameters
    strategy_match = re.search(r'strategy=<Config\[MegatronStrategy\((.*?)\)\]>', trainer_str, re.DOTALL)
    if strategy_match:
        strategy_content = strategy_match.group(1)
        strategy_params = {}
        
        strategy_patterns = {
            'tensor_model_parallel_size': r'tensor_model_parallel_size=(\d+)',
            'pipeline_model_parallel_size': r'pipeline_model_parallel_size=(\d+)',
            'virtual_pipeline_model_parallel_size': r'virtual_pipeline_model_parallel_size=(None|\d+)',
            'context_parallel_size': r'context_parallel_size=(\d+)',
            'sequence_parallel': r'sequence_parallel=(True|False)',
            'expert_model_parallel_size': r'expert_model_parallel_size=(\d+)',
            'pipeline_dtype': r'pipeline_dtype=(None|[^,\)]+)',
            'ckpt_async_save': r'ckpt_async_save=(True|False)',
            'ckpt_parallel_load': r'ckpt_parallel_load=(True|False)',
            'gradient_as_bucket_view': r'gradient_as_bucket_view=(True|False)',
            'ckpt_include_optimizer': r'ckpt_include_optimizer=(True|False)'
        }
        
        for param, pattern in strategy_patterns.items():
            match = re.search(pattern, strategy_content)
            if match:
                value = match.group(1)
                if value == 'None':
                    strategy_params[param] = None
                elif value in ['True', 'False']:
                    strategy_params[param] = value == 'True'
                elif param in ['tensor_model_parallel_size', 'pipeline_model_parallel_size', 
                              'context_parallel_size', 'expert_model_parallel_size']:
                    try:
                        strategy_params[param] = int(value)
                    except ValueError:
                        strategy_params[param] = value
                else:
                    strategy_params[param] = value
        
        # Extract DDP config
        ddp_match = re.search(r'ddp=<Config\[DistributedDataParallelConfig\((.*?)\)\]>', strategy_content, re.DOTALL)
        if ddp_match:
            ddp_content = ddp_match.group(1)
            ddp_params = {}
            
            ddp_patterns = {
                'grad_reduce_in_fp32': r'grad_reduce_in_fp32=(True|False)',
                'overlap_grad_reduce': r'overlap_grad_reduce=(True|False)',
                'overlap_param_gather': r'overlap_param_gather=(True|False)',
                'check_for_nan_in_grad': r'check_for_nan_in_grad=(True|False)',
                'average_in_collective': r'average_in_collective=(True|False)'
            }
            
            for param, pattern in ddp_patterns.items():
                match = re.search(pattern, ddp_content)
                if match:
                    ddp_params[param] = match.group(1) == 'True'
            
            strategy_params['ddp'] = ddp_params
        
        params['strategy'] = strategy_params
    
    # Extract callbacks (simplified)
    callbacks_match = re.search(r'callbacks=\[(.*?)\]', trainer_str)
    if callbacks_match:
        params['callbacks'] = callbacks_match.group(1)
    
    # Extract plugins (MegatronMixedPrecision)
    plugins_match = re.search(r'plugins=<Config\[MegatronMixedPrecision\((.*?)\)\]>', trainer_str, re.DOTALL)
    if plugins_match:
        plugins_content = plugins_match.group(1)
        plugins_params = {}
        
        plugins_patterns = {
            'precision': r"precision='([^']+)'",
            'params_dtype': r'params_dtype=([^,\)]+)',
            'pipeline_dtype': r'pipeline_dtype=([^,\)]+)',
            'autocast_enabled': r'autocast_enabled=(True|False)',
            'grad_reduce_in_fp32': r'grad_reduce_in_fp32=(True|False)'
        }
        
        for param, pattern in plugins_patterns.items():
            match = re.search(pattern, plugins_content)
            if match:
                value = match.group(1)
                if value in ['True', 'False']:
                    plugins_params[param] = value == 'True'
                else:
                    plugins_params[param] = value
        
        params['plugins'] = plugins_params
    
    return params

# ========== CONFIGURATION COMPARISON FUNCTIONS ==========

def remove_ignored_keys_deep(obj: Union[Dict, Any], ignored_keys: list) -> Union[Dict, Any]:
    """
    Recursively remove ignored keys from nested dictionaries.
    """
    if isinstance(obj, dict):
        return {
            key: remove_ignored_keys_deep(value, ignored_keys)
            for key, value in obj.items()
            if key not in ignored_keys
        }
    else:
        return obj

def find_differences(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> list:
    """
    Find all differences between two dictionaries and return them as a list.
    """
    differences = []
    
    # Check keys that exist in dict1 but not in dict2
    for key in dict1:
        current_path = f"{path}.{key}" if path else key
        if key not in dict2:
            differences.append(f"Key '{current_path}' exists in config1 but not in config2")
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            differences.extend(find_differences(dict1[key], dict2[key], current_path))
        elif dict1[key] != dict2[key]:
            differences.append(f"Key '{current_path}': config1='{dict1[key]}' != config2='{dict2[key]}'")
    
    # Check keys that exist in dict2 but not in dict1
    for key in dict2:
        current_path = f"{path}.{key}" if path else key
        if key not in dict1:
            differences.append(f"Key '{current_path}' exists in config2 but not in config1")
    
    return differences

def compare_all_arguments_detailed(config1: Dict[str, Any], config2: Dict[str, Any], 
                                 trainer_ignored_keys: list = ['log_every_n_steps', 'expert_model_parallel_size'],
                                 data_ignored_keys: list = [],
                                 debug: bool = False) -> tuple:
    """
    Compare model, data, and trainer configurations and return detailed differences.
    
    Returns:
        tuple: (are_same: bool, field_results: dict, all_differences: list)
    """
    arguments1 = config1.get('__arguments__', {})
    arguments2 = config2.get('__arguments__', {})
    
    field_results = {}
    all_differences = []
    
    # Compare MODEL field
    model1_str = arguments1.get('model', '')
    model2_str = arguments2.get('model', '')
    
    model_same = model1_str == model2_str
    field_results['model'] = model_same
    
    if not model_same:
        all_differences.append(f"MODEL field differs: config1='{model1_str}' != config2='{model2_str}'")
    
    if debug:
        print("DEBUG: Model comparison:")
        print(f"  Config1 model: {model1_str}")
        print(f"  Config2 model: {model2_str}")
        print(f"  Model same: {model_same}")
    
    # Compare DATA field (now with parameter parsing)
    data1_str = arguments1.get('data', '')
    data2_str = arguments2.get('data', '')
    
    # Parse data configurations
    data1_params = extract_data_params(data1_str)
    data2_params = extract_data_params(data2_str)
    
    # Remove ignored keys from data
    data1_clean = remove_ignored_keys_deep(data1_params, data_ignored_keys)
    data2_clean = remove_ignored_keys_deep(data2_params, data_ignored_keys)
    
    # Find data differences
    data_differences = find_differences(data1_clean, data2_clean)
    data_same = len(data_differences) == 0
    field_results['data'] = data_same
    
    if data_differences:
        all_differences.extend([f"DATA {diff}" for diff in data_differences])
    
    if debug:
        print(f"\nDEBUG: Data comparison (ignoring: {data_ignored_keys}):")
        print("  Data 1 params:")
        print(json.dumps(data1_params, indent=4, default=str))
        print("  Data 2 params:")
        print(json.dumps(data2_params, indent=4, default=str))
        print("  Data 1 cleaned:")
        print(json.dumps(data1_clean, indent=4, default=str))
        print("  Data 2 cleaned:")
        print(json.dumps(data2_clean, indent=4, default=str))
        print(f"  Data same: {data_same}")
        if data_differences:
            print("  Data differences:")
            for diff in data_differences:
                print(f"    - {diff}")
    
    # Compare TRAINER field (with ignored keys)
    trainer1_str = arguments1.get('trainer', '')
    trainer2_str = arguments2.get('trainer', '')

    # Parse trainer configurations
    trainer1_params = extract_trainer_params(trainer1_str)
    trainer2_params = extract_trainer_params(trainer2_str)
    
    # Remove ignored keys from trainer
    trainer1_clean = remove_ignored_keys_deep(trainer1_params, trainer_ignored_keys)
    trainer2_clean = remove_ignored_keys_deep(trainer2_params, trainer_ignored_keys)
    
    # Find trainer differences
    trainer_differences = find_differences(trainer1_clean, trainer2_clean)
    trainer_same = len(trainer_differences) == 0
    field_results['trainer'] = trainer_same
    
    if trainer_differences:
        all_differences.extend([f"TRAINER {diff}" for diff in trainer_differences])
    
    if debug:
        print(f"\nDEBUG: Trainer comparison (ignoring: {trainer_ignored_keys}):")
        print("  Trainer 1 params:")
        print(json.dumps(trainer1_params, indent=4, default=str))
        print("  Trainer 2 params:")
        print(json.dumps(trainer2_params, indent=4, default=str))
        print("  Trainer 1 cleaned:")
        print(json.dumps(trainer1_clean, indent=4, default=str))
        print("  Trainer 2 cleaned:")
        print(json.dumps(trainer2_clean, indent=4, default=str))
        print(f"  Trainer same: {trainer_same}")
        if trainer_differences:
            print("  Trainer differences:")
            for diff in trainer_differences:
                print(f"    - {diff}")
    
    # Overall result
    overall_same = model_same and data_same and trainer_same
    
    return overall_same, field_results, all_differences

def check_config_matches(base_config_path: str, generated_configs_dir: str, 
                        trainer_ignored_keys: list = ['log_every_n_steps', 'expert_model_parallel_size'],
                        data_ignored_keys: list = []) -> Tuple[bool, List[str]]:
    """
    Check if base config matches any generated configs and return which ones match.
    
    Returns:
        Tuple of (has_matches: bool, matching_files: List[str])
    """
    # Load base config
    try:
        with open(base_config_path, 'r') as f:
            base_config = json.load(f)
        print(f"Loaded base config from: {base_config_path}")
    except FileNotFoundError:
        print(f"Base config file not found: {base_config_path}")
        return False, []
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in base config: {e}")
        return False, []
    
    # Get all JSON files in the generated configs directory
    if not os.path.exists(generated_configs_dir):
        print(f"Generated configs directory not found: {generated_configs_dir}")
        return False, []
    
    json_files = [f for f in os.listdir(generated_configs_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"No JSON files found in: {generated_configs_dir}")
        return False, []
    
    # Filter out base_config.json from comparison
    other_files = [f for f in json_files if f != 'base_config.json' and f!= 'args.json']
    
    if not other_files:
        print("No other config files to compare")
        return False, []
    
    print(f"Found {len(other_files)} JSON files to compare")
    
    matching_files = []
    
    for filename in sorted(other_files):
        filepath = os.path.join(generated_configs_dir, filename)
        
        try:
            with open(filepath, 'r') as f:
                compare_config = json.load(f)
            
            # Compare all arguments (model, data, trainer)
            are_same, field_results, differences = compare_all_arguments_detailed(
                base_config, compare_config, 
                trainer_ignored_keys=trainer_ignored_keys,
                data_ignored_keys=data_ignored_keys,
                debug=False
            )
            
            if are_same:
                matching_files.append(filename)
        
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    print(f"{len(matching_files)} out of {len(other_files)} files match the base config")
    
    return len(matching_files) > 0, matching_files

# ========== CONFIGURATION VALUE EXTRACTION FUNCTIONS ==========

def extract_config_values_from_live_config(base_config) -> dict:
    """
    Extract configuration values directly from live Config objects (not JSON strings).
    This handles the case where base_config contains actual Config objects.
    """
    values = {
        'tp': 1,
        'pp': 1, 
        'cp': 1,
        'ep': 1,
        'vp': None,
        'mbs': 1,
        'gbs': 512,
        'nodes': 1,
        'seq_length': 8192
    }
    
    try:
        # Extract from trainer config object
        if hasattr(base_config, 'trainer'):
            trainer = base_config.trainer
            
            # Extract basic trainer params
            if hasattr(trainer, 'num_nodes'):
                values['nodes'] = trainer.num_nodes
                
            # Extract strategy params
            if hasattr(trainer, 'strategy'):
                strategy = trainer.strategy
                
                if hasattr(strategy, 'tensor_model_parallel_size'):
                    values['tp'] = strategy.tensor_model_parallel_size
                if hasattr(strategy, 'pipeline_model_parallel_size'):
                    values['pp'] = strategy.pipeline_model_parallel_size
                if hasattr(strategy, 'context_parallel_size'):
                    values['cp'] = strategy.context_parallel_size
                if hasattr(strategy, 'expert_model_parallel_size'):
                    values['ep'] = strategy.expert_model_parallel_size
                if hasattr(strategy, 'virtual_pipeline_model_parallel_size'):
                    values['vp'] = strategy.virtual_pipeline_model_parallel_size
        
        # Extract from data config object
        if hasattr(base_config, 'data'):
            data = base_config.data
            
            if hasattr(data, 'micro_batch_size'):
                values['mbs'] = data.micro_batch_size
            if hasattr(data, 'global_batch_size'):
                values['gbs'] = data.global_batch_size
            if hasattr(data, 'seq_length'):
                values['seq_length'] = data.seq_length
                
    except Exception as e:
        logger.warning(f"Error extracting from live config: {e}")
        # Return defaults
        
    return values

def extract_config_values_from_base_config(base_config) -> dict:
    # Case 1: base_config is a live Config object (not a dict)
    if not isinstance(base_config, dict):
        logger.debug("Extracting from live Config object")
        return extract_config_values_from_live_config(base_config)
    
    # Case 2: base_config is a dictionary
    logger.debug("Extracting from dict")
    
    # Check if this dict has __arguments__
    if '__arguments__' in base_config:
        arguments = base_config.get('__arguments__', {})
        
        # Check if arguments contain Config objects or strings
        trainer_obj = arguments.get('trainer', '')
        data_obj = arguments.get('data', '')
        
        # Case 2a: arguments contain Config objects (your case)
        if hasattr(trainer_obj, '__class__') and 'Config' in str(type(trainer_obj)):
            logger.debug("Arguments contain Config objects - extracting directly")
            
            # Create a temporary object to use the live config extraction
            class TempConfig:
                def __init__(self, trainer, data):
                    self.trainer = trainer
                    self.data = data
            
            temp_config = TempConfig(trainer_obj, data_obj)
            return extract_config_values_from_live_config(temp_config)
        
        # Case 2b: arguments contain string representations (compare_all_arguments_detailed case)
        elif isinstance(trainer_obj, str) and isinstance(data_obj, str):
            logger.debug("Arguments contain strings - parsing with regex")
            
            # Extract trainer string and parse it
            trainer_params = extract_trainer_params(trainer_obj)
            data_params = extract_data_params(data_obj)
            
            # Get strategy parameters
            strategy = trainer_params.get('strategy', {})
            
            values = {
                'tp': strategy.get('tensor_model_parallel_size', 1),
                'pp': strategy.get('pipeline_model_parallel_size', 1),
                'cp': strategy.get('context_parallel_size', 1),
                'ep': strategy.get('expert_model_parallel_size', 1),
                'vp': strategy.get('virtual_pipeline_model_parallel_size', None),
                'mbs': data_params.get('micro_batch_size', 1),
                'gbs': data_params.get('global_batch_size', 512),
                'nodes': trainer_params.get('num_nodes', 1),
                'seq_length': data_params.get('seq_length', 8192)
            }
            return values
    
    # Fallback: return defaults
    return {
        'tp': 1, 'pp': 1, 'cp': 1, 'ep': 1, 'vp': None,
        'mbs': 1, 'gbs': 512, 'nodes': 8, 'seq_length': 8192
    }

def create_log_dir_name(model_name: str, config_values: dict) -> str:
    """
    Create log directory name in the format: 
    llama_70b_8nodes_tp_4_pp_4_cp_2_ep_1_mbs_1_vp_5_seq_8192_gbs_512
    """
    vp = config_values.get('vp', 'None')
    if vp is None:
        vp = 'None'
    
    return (f"{model_name}_{config_values['nodes']}nodes_"
            f"tp_{config_values['tp']}_pp_{config_values['pp']}_"
            f"cp_{config_values['cp']}_ep_{config_values['ep']}_"
            f"mbs_{config_values['mbs']}_vp_{vp}_"
            f"seq_{config_values['seq_length']}_gbs_{config_values['gbs']}")

def compare_configs_with_type_handling(config1, config2, 
                                     trainer_ignored_keys: list = ['log_every_n_steps', 'expert_model_parallel_size'],
                                     data_ignored_keys: list = [],
                                     debug: bool = False) -> tuple:
    """
    Compare configurations handling both dict and live Config object types.
    
    Returns:
        tuple: (are_same: bool, field_results: dict, all_differences: list)
    """
    # Convert live Config objects to dict format for comparison
    def config_to_dict(config):
        if isinstance(config, dict):
            return config
        else:
            # Convert live Config object to dict-like structure
            try:
                return config.__dict__
            except:
                # Fallback: create a dict representation
                return {"__arguments__": {
                    "model": str(getattr(config, 'model', '')),
                    "data": str(getattr(config, 'data', '')),
                    "trainer": str(getattr(config, 'trainer', ''))
                }}
    
    config1_dict = config_to_dict(config1)
    config2_dict = config_to_dict(config2)
    
    return compare_all_arguments_detailed(
        config1_dict, config2_dict,
        trainer_ignored_keys=trainer_ignored_keys,
        data_ignored_keys=data_ignored_keys,
        debug=debug
    )

def safe_extract_config_values(base_config) -> dict:
    """
    Safe wrapper for extracting config values with error handling.
    """
    try:
        return extract_config_values_from_base_config(base_config)
    except Exception as e:
        logger.warning(f"Failed to extract config values: {e}")
        logger.warning(f"Base config type: {type(base_config)}")
        if hasattr(base_config, '__dict__'):
            logger.debug(f"Base config attributes: {list(base_config.__dict__.keys())}")
        
        # Return safe defaults
        return {
            'tp': 1, 'pp': 1, 'cp': 1, 'ep': 1, 'vp': None,
            'mbs': 1, 'gbs': 512, 'nodes': 8, 'seq_length': 8192
        }
