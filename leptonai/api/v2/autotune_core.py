"""
AutoTune core functionality.

This module contains the core AutoTune functionality with all extraction logic
delegated to the unified extraction system in autotune_utils.py
"""

import os
import json
import sys
import logging
import re
from functools import partial
from typing import Dict, Any, List, Optional, Tuple
from nemo.collections import llm
from nemo.collections.llm.tools.auto_configurator import AutoConfigurator, generate_configs, get_results
import nemo_run as run
from nemo.lightning.pytorch.callbacks.model_checkpoint import ModelCheckpoint

# Import the unified extraction system
from .autotune_utils_test import (
    validate_all_configs,
    check_config_matches,
    extract_all_values,
    extract_gpu_specs,
    create_log_dir_name,
    UnifiedExtractor
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ========== SIMPLIFIED MEMORY ESTIMATION ==========

def estimate_model_memory_usage_conservative(
    model_name: str,
    tp_size: int,
    pp_size: int,
    cp_size: int,
    micro_batch_size: int,
    seq_length: int,
    precision: str = "bf16",
    config_dict: Optional[Dict[str, Any]] = None
) -> float:
    """
    Estimate memory usage for a model configuration in GB.
    Now uses the ONE unified extraction function for everything.
    """

    """
    Conservative memory estimation that UNDERESTIMATES to avoid false positives.
    
    Only includes the most certain, unavoidable memory components:
    1. Model weights (100% certain)
    2. Optimizer states (100% certain for Adam)
    3. Gradients (100% certain)
    4. Minimal activation memory (conservative estimate)
    5. Minimal overhead (10% instead of 20%)
    
    EXCLUDES uncertain/variable components:
    - KV cache (varies greatly by implementation)
    - Complex activation calculations
    - Buffer memory estimates
    """

    # Get model info using unified extraction
    if config_dict:
        extracted_values = extract_all_values(config_dict)
        params_b = extracted_values.get('model_size_b')
        precision = extracted_values.get('precision', precision)
    else:
        extracted_values = extract_all_values(model_name)
        params_b = extracted_values.get('model_size_b')

    # Ultimate fallback for model size
    if params_b is None:
        params_b = 7  # Default to 7B

    # Bytes per parameter based on precision
    precision_bytes = {"fp32": 4, "fp16": 2, "bf16": 2, "int8": 1, "int4": 0.5}
    bytes_per_param = precision_bytes.get(precision.lower(), 2)

    # ========== COMPONENT 1: Model Parameters (100% CERTAIN) ==========
    # This is exact - we know the model size and precision
    model_memory_gb = (params_b * 1e9 * bytes_per_param) / (1024**3) / tp_size

    # ========== COMPONENT 2: Optimizer States (100% CERTAIN for Adam) ==========
    # Adam requires momentum + variance in fp32
    optimizer_memory_gb = (params_b * 1e9 * 4) / (1024**3) / tp_size

    # ========== COMPONENT 3: Gradients (100% CERTAIN) ==========
    # Must store gradients for backprop, same size as model weights
    gradient_memory_gb = model_memory_gb

    # ========== COMPONENT 4: Minimal Activation Memory (Conservative) ==========
    # A simple, conservative estimate based only on model size
    # Avoids complex calculations that might overestimate
    
    if params_b <= 7:
        base_activation_gb = 5.0
    elif params_b <= 13:
        base_activation_gb = 8.0
    elif params_b <= 30:
        base_activation_gb = 15.0
    elif params_b <= 70:
        base_activation_gb = 25.0
    else:
        base_activation_gb = params_b * 0.4  # 40% of model size for very large models
    
    # Scale with micro batch size (linear relationship)
    activation_memory_gb = base_activation_gb * micro_batch_size
    
    # Apply PP and CP distribution (activations do scale with these)
    activation_memory_gb = activation_memory_gb / pp_size / cp_size

    # ========== TOTAL: Sum Only the Certain Components ==========
    base_memory_gb = model_memory_gb + optimizer_memory_gb + gradient_memory_gb + activation_memory_gb

    # ========== Conservative Overhead (10% instead of 20%) ==========
    # Use lower overhead to underestimate total memory
    total_memory_gb = base_memory_gb * 1.1

    # Enhanced logging for transparency
    logger.debug(f"Conservative memory estimate for {model_name} ({params_b}B params, {precision}):")
    logger.debug(f"  Model weights: {model_memory_gb:.2f} GB")
    logger.debug(f"  Optimizer states: {optimizer_memory_gb:.2f} GB") 
    logger.debug(f"  Gradients: {gradient_memory_gb:.2f} GB")
    logger.debug(f"  Minimal activations: {activation_memory_gb:.2f} GB")
    logger.debug(f"  Base total: {base_memory_gb:.2f} GB")
    logger.debug(f"  With 10% overhead: {total_memory_gb:.2f} GB")
    logger.debug(f"  Parallelism: TP={tp_size}, PP={pp_size}, CP={cp_size}")
    logger.debug(f"  EXCLUDED: KV cache, buffers, complex activations (conservative approach)")

    return total_memory_gb

def check_cuda_oom_risk(
    config_values: Dict[str, Any],  # Already extracted values, not raw config
    resource_shape: str,
    model_name: str,
    safety_margin_gb: float = 5.0,
    memory_per_gpu: Optional[float] = None,
    base_config_dict: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, float, float]:
    """
    Check if a configuration will likely result in CUDA OOM.
    
    Args:
        config_values: Already-extracted configuration values dict (with 'tp', 'pp', 'cp', etc.)
        resource_shape: Resource shape string like "gpu.8xh200"
        model_name: Name of the model
        safety_margin_gb: Safety margin in GB to leave unused
        memory_per_gpu: Optional custom memory per GPU in GB
        base_config_dict: Optional base config dict for precision extraction
        
    Returns:
        Tuple of (will_oom: bool, reason: str, estimated_usage_gb: float, available_gb: float)
    """

    # Use unified GPU specs extraction
    gpu_type, gpu_count, gpu_memory_gb = extract_gpu_specs(resource_shape, memory_per_gpu)
    available_memory_gb = gpu_memory_gb - safety_margin_gb

    # Extract config values
    tp_size = config_values.get('tp', 1)
    pp_size = config_values.get('pp', 1)
    cp_size = config_values.get('cp', 1)
    micro_batch_size = config_values.get('mbs', 1)
    seq_length = config_values.get('seq_length', 8192)

    # Get precision
    if base_config_dict:
        base_values = extract_all_values(base_config_dict)
        precision = base_values.get('precision', 'bf16')
    else:
        precision = config_values.get('precision', 'bf16')

    # Use conservative memory estimation
    estimated_usage_gb = estimate_model_memory_usage_conservative(
        model_name=model_name,
        tp_size=tp_size,
        pp_size=pp_size,
        cp_size=cp_size,
        micro_batch_size=micro_batch_size,
        seq_length=seq_length,
        precision=precision,
        config_dict=base_config_dict
    )

    will_oom = estimated_usage_gb > available_memory_gb

    if will_oom:
        reason = (f"Conservative estimate ({estimated_usage_gb:.2f} GB) exceeds "
                 f"available memory ({available_memory_gb:.2f} GB) on {resource_shape}")
    else:
        reason = f"Configuration likely fits (conservative: {estimated_usage_gb:.2f} GB / {available_memory_gb:.2f} GB available)"

    return will_oom, reason, estimated_usage_gb, gpu_memory_gb

def validate_configurations_memory(
    configs: Dict[str, Any],
    base_config: Any,
    resource_shape: str,
    model_name: str,
    memory_per_gpu: Optional[float] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Validate all configurations for potential CUDA OOM issues.
    
    Args:
        configs: Dictionary of generated configurations
        base_config: Base configuration object
        resource_shape: Resource shape string
        model_name: Model name
        memory_per_gpu: Optional custom memory per GPU in GB
        
    Returns:
        Dictionary with memory analysis for each configuration
    """
    memory_analysis = {}
    
    # Convert base_config to dict if needed for extraction
    base_config_dict = None
    if hasattr(base_config, '__dict__'):
        base_config_dict = base_config.__dict__
    elif isinstance(base_config, dict):
        base_config_dict = base_config
    
    # Check base config using ONE unified extraction call
    base_config_values = extract_all_values(base_config)
    will_oom, reason, usage_gb, total_gb = check_cuda_oom_risk(
        base_config_values, resource_shape, model_name, 
        memory_per_gpu=memory_per_gpu, base_config_dict=base_config_dict
    )
    
    memory_analysis["base_config"] = {
        "will_oom": will_oom,
        "reason": reason,
        "estimated_usage_gb": usage_gb,
        "total_gpu_memory_gb": total_gb,
        "config_values": base_config_values
    }
    
    # Check each generated config using unified extraction call
    for config_name, config_obj in configs.items():
        config_values = extract_all_values(config_obj)
        
        # If extraction from object gave defaults, parse the config name
        if (config_values.get('tp') == 1 and config_values.get('pp') == 1 and 
            config_values.get('mbs') == 1 and config_values.get('gbs') == 512):
            name_values = extract_all_values(config_name)
            # Use name values if they seem more specific
            if (name_values.get('tp') != 1 or name_values.get('pp') != 1 or 
                name_values.get('mbs') != 1 or name_values.get('gbs') != 512):
                config_values = name_values
                logger.debug(f"Used config name parsing for {config_name}: {config_values}")
        
        will_oom, reason, usage_gb, total_gb = check_cuda_oom_risk(
            config_values, resource_shape, model_name,
            memory_per_gpu=memory_per_gpu, base_config_dict=base_config_dict
        )
        
        memory_analysis[config_name] = {
            "will_oom": will_oom,
            "reason": reason,
            "estimated_usage_gb": usage_gb,
            "total_gpu_memory_gb": total_gb,
            "config_values": config_values
        }
    
    return memory_analysis

# ========== CORE AUTOTUNE FUNCTIONS ==========

def generate_recipe_configs(args):
    """
    Generate AutoTune recipe configurations.
    Uses unified extraction system.
    Args:
        args: Arguments object with all configuration parameters
        
    Returns:
        dict: Dictionary containing:
            - base_config: Base configuration object
            - configs: Dictionary of generated configurations
            - runner: AutoConfigurator runner object
            - num_configs_generated: Number of configurations generated
            - base_config_matches: List of configs that match base config
            - memory_analysis: To know which configs will result in CUDA OOM 
    """
    is_valid, error_msg = validate_all_configs(args)
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_msg}")
    
    model_class = getattr(llm, args.model, None)
    if model_class is None:
        from .autotune_utils import get_supported_models
        supported_models = get_supported_models()
        raise ValueError(
            f"Model {args.model} not found in llm module. \n"
            f"Supported models: {', '.join(supported_models)}\n"
            f"For the latest list, check: https://github.com/NVIDIA/NeMo/blob/main/nemo/collections/llm/recipes/__init__.py"
        )
    
    recipe = partial(model_class.pretrain_recipe, num_nodes=args.nodes, num_gpus_per_node=args.gpus_per_node)()
    seq_length = getattr(args, 'seq_length', 8192)
    val_check_interval = getattr(args, 'val_check_interval', 50)
    max_steps = getattr(args, 'max_steps', 10)
    
    recipe.model.config.seq_length = recipe.data.seq_length = seq_length
    recipe.trainer.max_steps = max_steps
    recipe.trainer.val_check_interval = max_steps
    recipe.trainer.enable_checkpointing = False
    recipe.trainer.log_every_n_steps = 1
    recipe.trainer.limit_val_batches = 0
    recipe.trainer.strategy.ckpt_async_save = False
    checkpoint_callback = ModelCheckpoint(every_n_train_steps=1000000)
    recipe.trainer.callbacks.append(checkpoint_callback)

    # Use unified GPU specs extraction
    gpu_type, gpu_count, gpu_memory_gb = extract_gpu_specs(
        args.resource_shape, getattr(args, 'memory_per_gpu', None)
    )

    # Initialize Auto Configurator runner
    runner = AutoConfigurator(
        recipe=recipe,
        path_to_logs="/nemo-workspace/autoconfigurator/logs",
        gpu_memory_gb=gpu_memory_gb,
        tensor_parallel_sizes=args.tensor_parallel_sizes,
        pipeline_parallel_sizes=args.pipeline_parallel_sizes,
        virtual_pipeline_model_parallel_sizes=args.virtual_pipeline_model_parallel_sizes,
        context_parallel_sizes=args.context_parallel_sizes,
        micro_batch_sizes=args.micro_batch_sizes,
        global_batch_sizes=args.global_batch_sizes,
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

    logger.info("Performing CUDA OOM analysis for all configurations...")
    memory_analysis = validate_configurations_memory(
        configs, base_config, args.resource_shape, args.model, 
        memory_per_gpu=getattr(args, 'memory_per_gpu', None)
    )
    
    oom_configs = [name for name, analysis in memory_analysis.items() if analysis["will_oom"]]
    safe_configs = [name for name, analysis in memory_analysis.items() if not analysis["will_oom"]]
    
    logger.info(f"Memory Analysis Summary:")
    logger.info(f"  Total configurations: {len(memory_analysis)}")
    logger.info(f"  Safe configurations: {len(safe_configs)}")
    logger.info(f"  Potential OOM configurations: {len(oom_configs)}")
    
    if oom_configs:
        logger.warning(f"  Number of configurations with potential OOM: {len(oom_configs)}")

    # Save generated configs and check for matches
    save_generated_configs(args.model, base_config, configs)
    
    base_config_path = f"generated_configs/{args.model}/base_config.json"
    generated_configs_dir = f"generated_configs/{args.model}"

    has_matches, matching_files = check_config_matches(base_config_path, generated_configs_dir)
    
    base_config_matches = []
    
    if has_matches:
        for matching_file in matching_files:
            config_name = matching_file.replace('.json', '')
            if config_name in configs:
                base_config_matches.append(config_name)
                logger.info(f"Config '{config_name}' matches base config - will be flagged as base config equivalent")
        
        recipe.log.log_dir = "/nemo-workspace/autoconfigurator/logs/base_config"
        logger.info(f"Found {len(matching_files)} matching configs. Using original log_dir: {recipe.log.log_dir}")
    else:
        config_values = extract_all_values(base_config)
        new_log_dir = create_log_dir_name(args.model, config_values)
        recipe.log.log_dir = f"/nemo-workspace/autoconfigurator/logs/{new_log_dir}"
        logger.info(f"No matching configs found. Updated log_dir to: {recipe.log.log_dir}")

    return {
        'base_config': base_config,
        'configs': configs,
        'runner': runner,
        'num_configs_generated': len(configs),
        'base_config_matches': base_config_matches,
        'memory_analysis': memory_analysis
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

def lepton_executor(
    nodes: int, 
    devices: int,
    resource_shape: str = "gpu.8xh200",
    container_image: str = "nvcr.io/nvidia/nemo:25.02",
    nemo_run_dir: str = "/nemo-workspace/nemo-run",
    mount_path: str = "/nemo-workspace",
    mount_from: str = "node-nfs:shared",
    node_group: str = "nebius-h200-01",
    hf_token: Optional[str] = None,
    wandb_api_key: Optional[str] = None,
    torch_home: str = "/nemo-workspace/.cache",
    pythonpath: str = "/nemo-workspace/nemo-run:$PYTHONPATH"
) -> run.LeptonExecutor:
    """Create a Lepton executor for training with dynamic configuration."""
    mounts = [{
        "path": "/",
        "mount_path": mount_path,
        "from": mount_from
    }]

    env_vars = {
        "PYTHONPATH": pythonpath,
        "TORCH_HOME": torch_home,
    }
    
    if hf_token:
        env_vars["HF_TOKEN"] = hf_token
    if wandb_api_key:
        env_vars["WANDB_API_KEY"] = wandb_api_key

    return run.LeptonExecutor(
        resource_shape=resource_shape,
        container_image=container_image,
        nemo_run_dir=nemo_run_dir,
        mounts=mounts,
        node_group=node_group,
        nodes=nodes,
        nprocs_per_node=devices,
        env_vars=env_vars,
        launcher="torchrun",
    )

def run_pretraining_only(
    base_config, 
    configs: Dict, 
    base_config_matches: List[str] = None, 
    sequential: bool = False,
    executor_config: Dict[str, Any] = None,
    memory_analysis: Dict[str, Dict[str, Any]] = None,
    run_all: bool = False
):
    """Run pretraining only without results collection."""
    logger.info("Starting AutoTune pretraining...")
    
    if base_config_matches is None:
        base_config_matches = []
    
    if executor_config is None:
        executor_config = {}

    if memory_analysis is None:
        memory_analysis = {}

    configs_to_run = {}
    skipped_configs = {}
    base_config_will_run = True
    
    base_analysis = memory_analysis.get("base_config", {})
    base_will_oom = base_analysis.get("will_oom", False)
    
    if base_will_oom and not run_all:
        base_config_will_run = False
        skipped_configs["base_config"] = "Potential CUDA OOM"
        logger.warning("Skipping base_config due to potential CUDA OOM (use --run-all to force)")
    
    for config_name, config_obj in configs.items():
        analysis = memory_analysis.get(config_name, {})
        will_oom = analysis.get("will_oom", False)
        
        if will_oom and not run_all:
            skipped_configs[config_name] = "Potential CUDA OOM"
            logger.warning(f"Skipping {config_name} due to potential CUDA OOM (use --run-all to force)")
        else:
            configs_to_run[config_name] = config_obj

    total_configs = len(configs) + (1 if not base_config_matches else 0)
    configs_to_run_count = len(configs_to_run) + (1 if base_config_will_run and not base_config_matches else 0)
    skipped_count = len(skipped_configs)
    
    logger.info(f"Configuration filtering summary:")
    logger.info(f"  Total configurations: {total_configs}")
    logger.info(f"  Configurations to run: {configs_to_run_count}")
    logger.info(f"  Skipped configurations: {skipped_count}")
    
    if skipped_count > 0 and not run_all:
        logger.info(f"  Use --run-all flag to run all configurations including potential OOM ones")
    
    if configs_to_run_count == 0:
        logger.error("No configurations to run! All were filtered out due to potential OOM.")
        logger.error("Use --run-all flag to run anyway, or adjust your configuration parameters.")
        return {
            'total_configs': total_configs,
            'configs_run': 0,
            'configs_skipped': skipped_count,
            'skipped_configs': skipped_configs,
            'status': 'no_configs_to_run'
        }

    executor = lepton_executor(
        nodes=base_config.trainer.num_nodes,
        devices=base_config.trainer.devices,
        **executor_config
    )

    logger.info("Running filtered configurations...")

    with run.Experiment("pretrain-magic") as exp:
        if not base_config_matches and base_config_will_run:
            exp.add(base_config, executor=executor, name="base_config")
            logger.info("Added base_config to experiment")
        elif not base_config_matches and not base_config_will_run:
            logger.info("Skipped base_config due to potential CUDA OOM")
        else:
            logger.info(f"Skipping base_config as it matches: {', '.join(base_config_matches)}")
        
        idx = 1
        for config_name, recipe in configs_to_run.items():
            if config_name in base_config_matches:
                exp.add(recipe, executor=executor, name=f'{config_name}')
                logger.info(f"Added {config_name} as base_config_equivalent (matches base config)")
            else:
                exp.add(recipe, executor=executor, name=f'config-{idx}')
                logger.info(f"Added {config_name} as config-{idx}")
            idx = idx + 1

        exp.run(sequential=sequential)
    
    logger.info("AutoTune pretraining completed successfully!")
    if base_config_matches:
        logger.info(f"Note: Base config was not run separately as it matches {len(base_config_matches)} generated config(s)")
    
    if skipped_count > 0:
        logger.info(f"Note: {skipped_count} configuration(s) were skipped due to potential CUDA OOM")
    
    return {
        'total_configs': total_configs,
        'configs_run': configs_to_run_count,
        'configs_skipped': skipped_count,
        'skipped_configs': skipped_configs,
        'status': 'completed'
    }

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
        
    Returns:
        dict: Performance dictionary with configuration results
    """
    logger.info("Collecting AutoConfigurator results...")
    
    if base_config_matches is None:
        base_config_matches = []
    
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        logger.info(f"Results will be saved to: {output_file}")
        original_stdout = sys.stdout
        try:
            with open(output_file, 'w') as f:
                sys.stdout = f
                logger.info("=" * 80)
                logger.info("AUTOTUNE RESULTS - ALL CONFIGURATIONS")
                logger.info("=" * 80)
                logger.info(f"Total configurations generated: {num_configs_generated}")
                if base_config_matches:
                    logger.info(f"Base config matches found: {', '.join(base_config_matches)}")
                logger.info("=" * 80)
                
                performance_dict = get_results(
                    base_config=base_config,
                    train_config=runner,
                    path_to_save=path_to_logs,
                    output_top_n=output_top_n,
                    log_file_prefix=log_file_prefix,
                )
                
                logger.info("=" * 80)
                logger.info("END OF RESULTS")
                logger.info("=" * 80)
                
        finally:
            sys.stdout = original_stdout
        
        logger.info(f"All {num_configs_generated} configuration results saved to {output_file}")

        if output_top_n and output_top_n > 0:
            logger.info(f"Displaying top {output_top_n} results in terminal:")
            logger.info(f"\n{'='*60}")
            logger.info(f"TOP {output_top_n} AUTOTUNE RESULTS (Terminal Display)")
            logger.info(f"{'='*60}")
            if base_config_matches:
                logger.info(f"Note: Base config is equivalent to: {', '.join(base_config_matches)}")
            
            performance_dict = get_results(
                base_config=base_config,
                train_config=runner,
                path_to_save=path_to_logs,
                output_top_n=output_top_n,
                log_file_prefix=log_file_prefix,
            )
    else:
        logger.info(f"Displaying top {output_top_n} results in terminal:")
        if base_config_matches:
            logger.info(f"Note: Base config is equivalent to: {', '.join(base_config_matches)}")
        
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
