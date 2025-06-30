import os
import json
import re
import sys
from functools import partial
from typing import Dict, Any, Union, List, Tuple, Optional
from nemo.collections import llm
from nemo.collections.llm.tools.auto_configurator import AutoConfigurator, generate_configs, get_results
import nemo_run as run
import copy
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ========== VALIDATION FUNCTIONS ==========

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
    global_batch_size: int = None,
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
        global_batch_size: Global batch size (optional)
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
    
    if global_batch_size is not None and global_batch_size <= 0:
        return False, f"Global batch size must be positive, got: {global_batch_size}"
    
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
    }
    
    # Add optional parameters if they exist
    if hasattr(args, 'seq_length'):
        training_kwargs['seq_length'] = args.seq_length
    if hasattr(args, 'global_batch_size'):
        training_kwargs['global_batch_size'] = args.global_batch_size
    if hasattr(args, 'max_steps'):
        training_kwargs['max_steps'] = args.max_steps
    
    is_valid, error_msg = validate_training_settings(**training_kwargs)
    if not is_valid:
        return False, error_msg
    
    return True, ""

# ========== COMPARISON FUNCTIONS ==========

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
        logger.info("DEBUG: Model comparison:")
        logger.info(f"  Config1 model: {model1_str}")
        logger.info(f"  Config2 model: {model2_str}")
        logger.info(f"  Model same: {model_same}")
    
    # Compare DATA field
    data1_str = arguments1.get('data', '')
    data2_str = arguments2.get('data', '')
    
    data_same = data1_str == data2_str
    field_results['data'] = data_same
    
    if not data_same:
        all_differences.append(f"DATA field differs: config1='{data1_str}' != config2='{data2_str}'")
    
    if debug:
        logger.info("\nDEBUG: Data comparison:")
        logger.info(f"  Config1 data: {data1_str}")
        logger.info(f"  Config2 data: {data2_str}")
        logger.info(f"  Data same: {data_same}")
    
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
        logger.info(f"\nDEBUG: Trainer comparison (ignoring: {trainer_ignored_keys}):")
        logger.info("  Trainer 1 params:")
        logger.info(json.dumps(trainer1_params, indent=4, default=str))
        logger.info("  Trainer 2 params:")
        logger.info(json.dumps(trainer2_params, indent=4, default=str))
        logger.info("  Trainer 1 cleaned:")
        logger.info(json.dumps(trainer1_clean, indent=4, default=str))
        logger.info("  Trainer 2 cleaned:")
        logger.info(json.dumps(trainer2_clean, indent=4, default=str))
        logger.info(f"  Trainer same: {trainer_same}")
        if trainer_differences:
            logger.info("  Trainer differences:")
            for diff in trainer_differences:
                logger.info(f"    - {diff}")
    
    # Overall result
    overall_same = model_same and data_same and trainer_same
    
    return overall_same, field_results, all_differences

def check_config_matches(base_config_path: str, generated_configs_dir: str, 
                        trainer_ignored_keys: list = ['log_every_n_steps', 'expert_model_parallel_size']) -> Tuple[bool, List[str]]:
    """
    Check if base config matches any generated configs and return which ones match.
    
    Returns:
        Tuple of (has_matches: bool, matching_files: List[str])
    """
    # Load base config
    try:
        with open(base_config_path, 'r') as f:
            base_config = json.load(f)
        logger.info(f"Loaded base config from: {base_config_path}")
    except FileNotFoundError:
        logger.error(f"Base config file not found: {base_config_path}")
        return False, []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in base config: {e}")
        return False, []
    
    # Get all JSON files in the generated configs directory
    if not os.path.exists(generated_configs_dir):
        logger.error(f"Generated configs directory not found: {generated_configs_dir}")
        return False, []
    
    json_files = [f for f in os.listdir(generated_configs_dir) if f.endswith('.json')]
    
    if not json_files:
        logger.info(f"No JSON files found in: {generated_configs_dir}")
        return False, []
    
    # Filter out base_config.json from comparison
    other_files = [f for f in json_files if f != 'base_config.json' and f!= 'args.json']
    
    if not other_files:
        logger.info("No other config files to compare")
        return False, []
    
    logger.info(f"Found {len(other_files)} JSON files to compare")
    
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
                debug=False
            )
            
            if are_same:
                matching_files.append(filename)
        
        except Exception as e:
            logger.warning(f"Error processing {filename}: {e}")
            continue
    
    logger.info(f"{len(matching_files)} out of {len(other_files)} files match the base config")
    
    return len(matching_files) > 0, matching_files

def extract_config_values_from_base_config(base_config: dict) -> dict:
    """
    Extract the required values from base_config to create the log directory name
    """
    arguments = base_config.get('__arguments__', {})
    
    # Extract trainer string and parse it
    trainer_str = arguments.get('trainer', '')
    trainer_params = extract_trainer_params(trainer_str)
    
    # Extract data string to get micro_batch_size
    data_str = arguments.get('data', '')
    micro_batch_size = 1  # default
    
    # Extract micro_batch_size from data string
    mbs_match = re.search(r'micro_batch_size=(\d+)', data_str)
    if mbs_match:
        micro_batch_size = int(mbs_match.group(1))
    
    # Get strategy parameters
    strategy = trainer_params.get('strategy', {})
    
    values = {
        'tp': strategy.get('tensor_model_parallel_size', 1),
        'pp': strategy.get('pipeline_model_parallel_size', 1),
        'cp': strategy.get('context_parallel_size', 1),
        'ep': strategy.get('expert_model_parallel_size', 1),  # default to 1 if not found
        'mbs': micro_batch_size,
        'nodes': trainer_params.get('num_nodes', 1)
    }
    
    return values

def create_log_dir_name(model_name: str, config_values: dict) -> str:
    """
    Create log directory name in the format: 
    nemotron_4b_1nodes_tp_<>_pp_<>_cp_<>_ep_<>_mbs_<>_vp_None
    """
    return f"{model_name}_{config_values['nodes']}nodes_tp_{config_values['tp']}_pp_{config_values['pp']}_cp_{config_values['cp']}_ep_{config_values['ep']}_mbs_{config_values['mbs']}_vp_None"

# ========== CORE AUTOTUNE FUNCTIONS ==========

def generate_recipe_configs(args):
    """
    Generate AutoTune recipe configurations.
    
    Args:
        args: Arguments object with all configuration parameters
        
    Returns:
        tuple: (base_config, configs, runner, num_configs_generated, base_config_matches)
    """
    # Validate configurations before proceeding
    is_valid, error_msg = validate_all_configs(args)
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_msg}")
    
    # Import recipe and change needed parameters dynamically
    model_class = getattr(llm, args.model, None)
    if model_class is None:
        supported_models = get_supported_models()
        raise ValueError(
            f"Model {args.model} not found in llm module. \n"
            f"Supported models: {', '.join(supported_models)}\n"
            f"For the latest list, check: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py"
        )
    
    recipe = partial(model_class.pretrain_recipe, num_nodes=args.nodes, num_gpus_per_node=args.gpus_per_node)()
    
    # Configure recipe parameters with validation
    seq_length = getattr(args, 'seq_length', 8192)
    global_batch_size = getattr(args, 'global_batch_size', 512)
    val_check_interval = getattr(args, 'val_check_interval', 10)
    max_steps = getattr(args, 'max_steps', 10)
    
    recipe.model.config.seq_length = recipe.data.seq_length = seq_length
    recipe.data.global_batch_size = global_batch_size
    recipe.trainer.val_check_interval = val_check_interval
    recipe.trainer.max_steps = max_steps

    # Initialize Auto Configurator runner
    runner = AutoConfigurator(
        recipe=recipe,
        path_to_logs="/nemo-workspace/autoconfigurator/logs",
        gpu_memory_gb=80,
        tensor_parallel_sizes=args.tensor_parallel_sizes,
        pipeline_parallel_sizes=args.pipeline_parallel_sizes,
        context_parallel_sizes=args.context_parallel_sizes,
        micro_batch_sizes=args.micro_batch_sizes,
        max_model_parallel_size=args.max_model_parallel_size,
        min_model_parallel_size=args.min_model_parallel_size,
        max_steps_per_run=args.max_steps_per_run,
        max_minutes_per_run=args.max_minutes_per_run,
        num_tokens_in_b=args.num_tokens_in_b,
        vocab_size=args.vocab_size,
        calculate_model_size=False,
    )

    base_config, configs = generate_configs(runner)
    num_configs_generated = len(configs)

    # Check if configs match and adjust log_dir accordingly
    save_generated_configs(args.model, base_config, configs)
    
    base_config_path = f"generated_configs/{args.model}/base_config.json"
    generated_configs_dir = f"generated_configs/{args.model}"
    
    # Check if there are matching configurations
    has_matches, matching_files = check_config_matches(base_config_path, generated_configs_dir)
    
    base_config_matches = []
    
    if has_matches:
        # Track the matching configs as base config equivalents
        for matching_file in matching_files:
            config_name = matching_file.replace('.json', '')
            if config_name in configs:
                # Just track the match, don't modify the config object
                base_config_matches.append(config_name)
                logger.info(f"Config '{config_name}' matches base config - will be flagged as base config equivalent")
        
        # Keep the original log directory
        recipe.log.log_dir = "/nemo-workspace/autoconfigurator/logs/base_config"
        logger.info(f"Found {len(matching_files)} matching configs. Using original log_dir: {recipe.log.log_dir}")
    else:
        # Extract configuration values and create new log directory name
        config_values = extract_config_values_from_base_config(base_config.__dict__)
        new_log_dir = create_log_dir_name(args.model, config_values)
        
        # Update the log directory
        recipe.log.log_dir = f"/nemo-workspace/autoconfigurator/logs/{new_log_dir}"
        logger.info(f"No matching configs found. Updated log_dir to: {recipe.log.log_dir}")

    return {
        'base_config': base_config,
        'configs': configs,
        'runner': runner,
        'num_configs_generated': len(configs),
        'base_config_matches': base_config_matches
    }

def save_generated_configs(model_name: str, base_config, configs: Dict):
    """
    Save generated configurations to disk.
    
    Args:
        model_name: Name of the model
        base_config: Base configuration object
        configs: Dictionary of configuration objects
    """
    os.makedirs("generated_configs", exist_ok=True)
    model_dir = os.path.join("generated_configs", model_name)
    os.makedirs(model_dir, exist_ok=True)

    with open(os.path.join(model_dir, "base_config.json"), "w") as f:
        json.dump(base_config.__dict__, f, indent=4, default=str)

    for config_name, recipe in configs.items():
        with open(os.path.join(model_dir, f"{config_name}.json"), "w") as f:
            json.dump(recipe.__dict__, f, indent=4, default=str)

def lepton_executor(nodes: int, devices: int) -> run.LeptonExecutor:
    """
    Create a Lepton executor for training.
    
    Args:
        nodes: Number of nodes
        devices: Number of devices per node
        
    Returns:
        LeptonExecutor instance
    """
    mounts = [
        {
            "path": "/",
            "mount_path": "/nemo-workspace",
            "from": "node-nfs:shared"
        }
    ]

    return run.LeptonExecutor(
        resource_shape="gpu.8xh200",
        container_image="nvcr.io/nvidia/nemo:25.02",
        nemo_run_dir="/nemo-workspace/nemo-run",
        mounts=mounts,
        node_group="nebius-h200-01",
        nodes=nodes,
        nprocs_per_node=devices,
        env_vars={
            "PYTHONPATH": "/nemo-workspace/nemo-run:$PYTHONPATH",
            "TORCH_HOME": "/nemo-workspace/.cache",
            "HF_TOKEN": "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",
            "WANDB_API_KEY": "b3643404c5a40a18ba74710102bcbc9248e67765"
        },
        launcher="torchrun",
    )

def run_pretraining_only(base_config, configs: Dict, base_config_matches: List[str] = None, sequential: bool = False):
    """
    Run pretraining only without results collection.
    
    Args:
        base_config: Base configuration object
        configs: Dictionary of configuration objects
        base_config_matches: List of config names that match base config (to avoid duplicate runs)
        sequential: Whether to run configurations sequentially
    """
    logger.info("Starting AutoTune pretraining...")
    
    if base_config_matches is None:
        base_config_matches = []
    
    # Initialize executor for base config
    executor = lepton_executor(
        nodes=base_config.trainer.num_nodes,
        devices=base_config.trainer.devices
    )

    # Run base config and other configs
    logger.info("Running base config...")
    executor = lepton_executor(nodes=4, devices=8)

    with run.Experiment("pretrain-magic") as exp:
        # Only add base config if no configs match it
        if not base_config_matches:
            exp.add(base_config, executor=executor, name="base_config")
            logger.info("Added base_config to experiment")
        else:
            logger.info(f"Skipping base_config as it matches: {', '.join(base_config_matches)}")
        
        # Launch the experiment on the cluster
        idx = 1
        for config_name, recipe in configs.items():
            if config_name in base_config_matches:
                # This config matches base config, so mark it specially but still run it
                exp.add(recipe, executor=executor, name=f'base_config_equivalent_{config_name}')
                logger.info(f"Added {config_name} as base_config_equivalent (matches base config)")
            else:
                exp.add(recipe, executor=executor, name=f'config-{idx}')
                logger.info(f"Added {config_name} as config-{idx}")
            idx = idx + 1

        exp.run(sequential=sequential)
    
    logger.info("AutoTune pretraining completed successfully!")
    if base_config_matches:
        logger.info(f"Note: Base config was not run separately as it matches {len(base_config_matches)} generated config(s)")
    
    return len(configs) + (0 if base_config_matches else 1)  # Return total configs run

def get_results_with_output(
    base_config,
    runner,
    path_to_logs: str,
    log_file_prefix: str,
    num_configs_generated: int,
    base_config_matches: List[str] = None,
    output_file: Optional[str] = None,
    output_top_n: int = 10
):
    """
    Get AutoConfigurator results with optional file output.
    
    Args:
        base_config: Base configuration object
        runner: AutoConfigurator runner
        path_to_logs: Path to logs directory
        log_file_prefix: Log file prefix
        num_configs_generated: Total number of configs generated
        base_config_matches: List of config names that match base config
        output_file: Optional output file path
        output_top_n: Number of top configurations to display in terminal
    """
    logger.info("Collecting AutoConfigurator results...")
    
    if base_config_matches is None:
        base_config_matches = []
    
    if output_file:
        # Create directory for the file if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        logger.info(f"Results will be saved to: {output_file}")
        print("Checking HERE UHHH")
        # Redirect stdout to capture all results for file output
        original_stdout = sys.stdout
        try:
            # First get all results (no top_n limit for file output)
            with open(output_file, 'w') as f:
                sys.stdout = f
                # Write header information
                print("=" * 80)
                print("AUTOTUNE RESULTS - ALL CONFIGURATIONS")
                print("=" * 80)
                print(f"Total configurations generated: {num_configs_generated}")
                if base_config_matches:
                    print(f"Base config matches found: {', '.join(base_config_matches)}")
                print("=" * 80)
                print()
                
                # Get all results without top_n limit
                performance_dict = get_results(
                    base_config=base_config,
                    train_config=runner,
                    path_to_save=path_to_logs,
                    output_top_n=output_top_n,
                    log_file_prefix=log_file_prefix,
                )
                
                print()
                print("=" * 80)
                print("END OF RESULTS")
                print("=" * 80)
                
        finally:
            sys.stdout = original_stdout
        
        logger.info(f"All {num_configs_generated} configuration results saved to {output_file}")
        
        # Now display top_n results in terminal
        if output_top_n and output_top_n > 0:
            logger.info(f"Displaying top {output_top_n} results in terminal:")
            print(f"\n{'='*60}")
            print(f"TOP {output_top_n} AUTOTUNE RESULTS (Terminal Display)")
            print(f"{'='*60}")
            if base_config_matches:
                print(f"Note: Base config is equivalent to: {', '.join(base_config_matches)}")
            print()
            
            performance_dict = get_results(
                base_config=base_config,
                train_config=runner,
                path_to_save=path_to_logs,
                output_top_n=output_top_n,
                log_file_prefix=log_file_prefix,
            )
    else:
        # No output file, just display top_n in terminal
        logger.info(f"Displaying top {output_top_n} results in terminal:")
        if base_config_matches:
            print(f"Note: Base config is equivalent to: {', '.join(base_config_matches)}")
        
        performance_dict = get_results(
            base_config=base_config,
            train_config=runner,
            path_to_save=path_to_logs,
            output_top_n=output_top_n,
            log_file_prefix=log_file_prefix,
        )
        logger.info(f"Results displayed in terminal using path: {path_to_logs} with prefix: {log_file_prefix}")
        
    logger.info(f"Results collection completed. Total configs: {num_configs_generated}, Base config matches: {len(base_config_matches)}")

    return performance_dict

def run_pretraining(args):
    """
    Backwards-compatible function that handles both pretraining and results based on args.
    
    Args:
        args: Arguments object with all configuration parameters
    """
    # Validate configurations before running
    is_valid, error_msg = validate_all_configs(args)
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_msg}")

    result = generate_recipe_configs(args)

    if args.get_results:
        # Handle results collection
        output_file = getattr(args, 'output_file', None)
        get_results_with_output(
            base_config=result['base_config'],
            runner=result['runner'],
            path_to_logs=args.path_to_logs,
            log_file_prefix=args.log_file_prefix,
            num_configs_generated=result['num_configs_generated'],
            base_config_matches=result['base_config_matches'],
            output_file=output_file,
            output_top_n=result['num_configs_generated']
        )
    else:
        # Handle pretraining
        sequential = getattr(args, 'sequential', False)
        total_runs = run_pretraining_only(base_config, configs, base_config_matches, sequential)
        logger.info(f"Total configurations executed: {total_runs}")
