# Tuna User Guide
---
## <span style="color:DeepSkyBlue">`Data` Management Commands
---
The `Data` commands allow users to manage their data within the Tuna platform. These commands provide options for listing, uploading, and removing data files, making it easy to interact with and manage datasets.

### <span style="color:SkyBlue">`list-data` Command Overview

The `list-data` command allows users to list all existing data files available in their Tuna environment. This command provides a simple way to view and verify the available datasets.

#### Example Usage

```bash
lep tuna list-data
```

In this example, the command lists all data files in the Tuna environment, showing their names and details.

### <span style="color:SkyBlue">`upload-data` Command Overview

The `upload-data` command allows users to upload a new data file to the Tuna platform. The user needs to specify the local file path and provide a name for the data file.

#### Example Usage

```bash
lep tuna upload-data --file <local_file_path> --name <data_file_name>
```

In this example, the command uploads a data file from the specified local path and assigns the provided name to it in the Tuna environment.

### <span style="color:SkyBlue">`remove-data` Command Overview

The `remove-data` command allows users to delete an existing data file from the Tuna environment. The user must specify the name of the data file to be deleted.

#### Example Usage

```bash
lep tuna remove-data --name <data_file_name>
```

In this example, the command deletes the specified data file from the Tuna environment.
		
---

## <span style="color:DeepSkyBlue">`Model` Management Commands
---
    
### <span style="color:SkyBlue">`train` Command Overview

The `train` function allows users to configure and run a training job for fine-tuning machine learning models with various customizable options. The command supports several options for specifying model configurations, training parameters, and environment settings. 

#### Example Usage

```bash
lep tuna train -n my-tuna-model --resource-shape gpu.a10 --env HF_TOKEN=<your huggingface token> --model-path=meta-llama/Meta-Llama-3-8B-Instruct -dn=<file name you uploaded with upload-data> --num-train-epochs=2 --per-device-train-batch-size=16 --gradient-accumulation-steps=4 --learning-rate=0.0001 --lora --early-stop-threshold=0.01
```

In this example, the command trains a model named "my-tuna-model" using the specified model path and dataset, with custom training parameters such as number of epochs, learning rate, and LoRA settings

#### CLI Options

1. **`--name` / `-n`** (Required):
   - **Type**: `str`
   - **Description**: Assigns a unique identifier to the tuna model being trained. It ensures that the name adheres to certain constraints (prefix and length limit).

2. **`--env` / `-e`**:
   - **Type**: `tuple`
   - **Description**: Specifies environment variables to pass to the job in the format `NAME=VALUE`. Multiple environment variables can be provided.

3. **`--model-path`** (Required):
   - **Type**: `str`
   - **Description**: Specifies the base model path for fine-tuning. This can be a HuggingFace model ID or a local directory path containing the model.

4. **`--dataset-name` / `-dn`** (Required):
   - **Type**: `click.Path`
   - **Description**: Path to the dataset used for training.

5. **`--num-train-epochs`**:
   - **Type**: `int`
   - **Description**: Number of training epochs. Default is `10`.

6. **`--per-device-train-batch-size`**:
   - **Type**: `int`
   - **Description**: Batch size per device (GPU or CPU) used for training. Default is `32`.

7. **`--gradient-accumulation-steps`**:
   - **Type**: `int`
   - **Description**: Number of gradient accumulation steps. Default is `1`.

8. **`--report-wandb`**:
   - **Type**: `flag`
   - **Description**: If set, reports training metrics to Weights and Biases (wandb). Requires WANDB_API_KEY to be set in the environment variables.

9. **`--wandb-project`**:
    - **Type**: `str`
    - **Description**: Specifies the wandb project to report to, only effective when `--report-wandb` is set.

10. **`--learning-rate`**:
    - **Type**: `float`
    - **Description**: Specifies the learning rate for the training. Default is `5e-5`.

11. **`--warmup-ratio`**:
    - **Type**: `float`
    - **Description**: Specifies the warmup ratio for learning rate scheduling. Default is `0.1`.

12. **`--lora`**:
    - **Type**: `flag`
    - **Description**: If set, uses Low-Rank Adaptation (LoRA) instead of full model fine-tuning.

13. **`--lora-rank`**:
    - **Type**: `int`
    - **Description**: Specifies the rank for LoRA, effective only when `--lora` is set. Default is `8`.

14. **`--lora-alpha`**:
    - **Type**: `int`
    - **Description**: Specifies the alpha parameter for LoRA, effective only when `--lora` is set. Default is `16`.

15. **`--lora-dropout`**:
    - **Type**: `float`
    - **Description**: Specifies the dropout rate for LoRA, effective only when `--lora` is set. Default is `0.1`.

16. **`--medusa`**:
    - **Type**: `flag`
    - **Description**: If set, trains a Medusa heads model instead of performing fine-tuning.

17. **`--num-medusa-head`**:
    - **Type**: `int`
    - **Description**: Specifies the number of Medusa heads, effective only when `--medusa` is set. Default is `4`.

18. **`--early-stop-threshold`**:
    - **Type**: `float`
    - **Description**: Specifies an early stopping threshold. Training stops early if the reduction in validation loss is less than this threshold for a set number of epochs. Default is `0.01`.



### <span style="color:SkyBlue">`run` Command Overview

The `run` command allows users to execute a specified tuna model. This command checks if the model exists, verifies its training status, and ensures necessary configurations, such as secrets and storage, are set before deploying the model.

#### Example Usage

```bash
lep tuna run --name my-tuna-model --hf-transfer --tuna-step 5 --use-int --huggingface-token HUGGING_FACE_HUB_TOKEN --mount /path/to/storage:/mnt/storage
```

In this example, the command runs the model named "my-tuna-model" with various options, including faster Hugging Face transfers, token generation steps, and GPU memory optimizations.

#### CLI Options

1. **`--name` / `-n`** (Required):
   - **Type**: `str`
   - **Description**: Name of the tuna model to run. This is a required option.

2. **`--hf-transfer`**:
   - **Type**: `flag`
   - **Default**: `True`
   - **Description**: Enables faster uploads and downloads from the Hugging Face Hub using `hf_transfer`.

3. **`--tuna-step`**:
   - **Type**: `int`
   - **Default**: `3`
   - **Description**: Minimum number of tokens to generate in each new chunk in streaming mode. Lower values send results faster but may increase network overhead.

4. **`--use-int`**:
   - **Type**: `flag`
   - **Default**: `True`
   - **Description**: Enables quantization techniques to reduce GPU memory usage. Suitable for models under 7B or 13B.

5. **`--huggingface-token`**:
   - **Type**: `str`
   - **Default**: `"HUGGING_FACE_HUB_TOKEN"`
   - **Description**: The name of your Hugging Face token, which must be set as a secret in the workspace.

6. **`--mount`**:
   - **Type**: `tuple`
   - **Description**: Persistent storage to be mounted to the deployment, specified in the format `STORAGE_PATH:MOUNT_PATH`. This option can be repeated for multiple mount points.

#### Command Execution

When the `run` command is executed, it checks the following:
- If the specified model exists in the Tuna environment.
- If the model has completed training or if the training has failed.
- If the required Hugging Face token exists as a secret in the workspace.

The command then prepares the deployment by generating appropriate paths, setting environment variables, and configuring mounts, before invoking the `deployment_create` command to deploy the model.

If the model has LoRA or Medusa configurations, they will be appropriately set in the environment variables during deployment.

```bash
lep tuna run --name my-tuna-model
```

This example will deploy the model named "my-tuna-model" with the default settings. You can further customize the deployment by adding additional options like `--hf-transfer`, `--tuna-step`, `--use-int`, and more.


### <span style="color:SkyBlue">`list` Command Overview

The `list` command allows users to display all tuna models available in the current workspace. It can display the models either in a table format (default) or in a list format for easier readability on small screens. The command includes detailed information about each model, such as its status, training date, data source, and deployments.

#### Example Usage

```bash
lep tuna list
```

This command displays a table of all tuna models along with details such as name, training status, model type, data source, and any running deployments.

To display the models in a list format (useful for small screens), you can use the `--list-view` option:

```bash
lep tuna list --list-view
```
or
```bash
lep tuna list -l
```

#### CLI Options

1. **`--list-view` / `-l`**:
   - **Type**: `flag`
   - **Default**: `False`
   - **Description**: If set, models will be displayed in a list format instead of a table. This is useful for users on small screens or terminals where table view might be hard to read.

### Command Execution

The `list` command offers two views:

1. **Table View (Default)**:
   - Displays models in a table format with columns for **Name**, **Trained At**, **Model**, **Data**, **Lora or Medusa**, **State**, **Deployments Name**, and **Train Job Name**. Each column provides specific details about the model's configuration and status.
   
   Example:

   ```bash
   lep tuna list
   ```

   Output in table format:
   
   ```
   +-------------------------------------+-------------+--------------------+----------------+--------------+------------------+-------------------------+------------------+
   | Name                                | Trained At  | Model              | Data           | Lora or Medusa | State            | Deployments Name        | Train Job Name   |
   +-------------------------------------+-------------+--------------------+----------------+--------------+------------------+-------------------------+------------------+
   | my-tuna-model                       | 2023-12-01  | llama-8b          | dataset-v1     | Lora          | Running          | deployment1, deployment2 | train-job-123    |
   +-------------------------------------+-------------+--------------------+----------------+--------------+------------------+-------------------------+------------------+
   ```

2. **List View**:
   - Displays models in a list format where each model’s details are presented one by one with proper indentation for easy reading on smaller screens.
   
   Example:

   ```bash
   lep tuna list --list-view
   ```

   Output in list format:

   ```
   1. Name: my-tuna-model
       Trained At: 2023-12-01
       Model: llama-8b
       Data: dataset-v1
       Lora or Medusa: Lora
       State: Running
       Deployments Name: deployment1, deployment2
       Train Job Name: train-job-123
   --------------------------------------------------
   ```


### <span style="color:SkyBlue">`remove` Command Overview

The `remove` function allows users to delete a specified tuna model. It verifies if the model exists, checks for any active deployments, and prompts the user for confirmation before deleting the model and any associated resources.

#### Example Usage

```bash
lep tuna remove -n my-tuna-model
```

In this example, the command removes a model named "my-tuna-model". It will check if the model exists, and if there are any active deployments or jobs associated with the model, it prompts the user for confirmation before proceeding with the deletion.

#### CLI Options

1. **`--name` / `-n`** (Required):
   - **Type**: `str`
   - **Description**: Name of the model to be deleted. It is a required argument that specifies the unique identifier of the model.

### <span style="color:SkyBlue">`info` Command Overview

The `info` function retrieves and prints the details of a specified tuna model. It checks if the model exists and provides detailed information about the model configuration and status.

#### Example Usage

```bash
lep tuna info -n my-tuna-model
```

In this example, the command retrieves the information for a model named "my-tuna-model". If the model does not exist, it prompts the user to check their available models.

#### CLI Options

1. **`--name` / `-n`** (Required):
   - **Type**: `str`
   - **Description**: Name of the tuna model to retrieve details for. It is a required argument to specify the model.

### <span style="color:SkyBlue">`clear_failed_models` Command Overview

The `clear_failed_models` function deletes all failed training models and any related jobs. It iterates through all models, identifies those with a training failure status, and deletes them along with any associated jobs or resources.

#### Example Usage

```bash
lep tuna clear_failed_models
```

In this example, the command clears all models that have failed during training. It removes their associated storage files and any jobs linked to the failed models, ensuring a clean environment.