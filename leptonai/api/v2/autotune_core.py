"""
AutoTune core functionality for generating configurations and running training.

This module contains the core AutoTune functionality including:
- Configuration generation using AutoConfigurator
- Training execution with Lepton executor
- Results collection and analysis
"""

import os
import json
import sys
import logging
from functools import partial
from typing import Dict, Any, List, Optional
from nemo.collections import llm
from nemo.collections.llm.tools.auto_configurator import AutoConfigurator, generate_configs, get_results
import nemo_run as run

from .autotune_utils import (
    validate_all_configs,
    check_config_matches,
    extract_config_values_from_base_config,
    create_log_dir_name,
    safe_extract_config_values
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ========== CORE AUTOTUNE FUNCTIONS ==========

def generate_recipe_configs(args):
    """
    Generate AutoTune recipe configurations.
    
    Args:
        args: Arguments object with all configuration parameters
        
    Returns:
        dict: Dictionary containing:
            - base_config: Base configuration object
            - configs: Dictionary of generated configurations
            - runner: AutoConfigurator runner object
            - num_configs_generated: Number of configurations generated
            - base_config_matches: List of configs that match base config
    """
    # Validate configurations before proceeding
    is_valid, error_msg = validate_all_configs(args)
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_msg}")
    
    # Import recipe and change needed parameters dynamically
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
    recipe.trainer.val_check_interval = max_steps
    recipe.trainer.max_steps = max_steps
    recipe.trainer.enable_checkpointing = False
    recipe.trainer.val_check_interval = max_steps
    recipe.trainer.log_every_n_steps = 1
    recipe.trainer.limit_val_batches = 0

    # Initialize Auto Configurator runner
    runner = AutoConfigurator(
        recipe=recipe,
        path_to_logs="/nemo-workspace/autoconfigurator/logs",
        gpu_memory_gb=80,
        tensor_parallel_sizes=args.tensor_parallel_sizes,
        pipeline_parallel_sizes=args.pipeline_parallel_sizes,
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
        
    Returns:
        int: Number of configurations executed
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
    executor = lepton_executor(nodes=8, devices=8)

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
            print("IMPORTANT I GUESS")
            print(recipe)
            if config_name in base_config_matches:
                # This config matches base config, so mark it specially but still run it
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
        
    Returns:
        dict: Performance dictionary with configuration results
    """
    logger.info("Collecting AutoConfigurator results...")
    
    if base_config_matches is None:
        base_config_matches = []
    
    if output_file:
        # Create directory for the file if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        logger.info(f"Results will be saved to: {output_file}")
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
