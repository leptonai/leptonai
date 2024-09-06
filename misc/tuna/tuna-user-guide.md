# Tuna User Guide
---
# <span style="color:DeepSkyBlue"> Example Workflow
---
Here's a streamlined example demonstrating how to upload a dataset, train a model, and deploy it using Tuna commands. This workflow guides you through the steps of managing a machine learning model, from data preparation to deployment.

#### Step 1: Upload Data

Start by uploading a dataset (`sample.json`) from your local system to Tuna's data storage.

```bash
lep tuna upload-data --file /path/to/your/data/sample.json --name sample.json
```

**Output:**

```plaintext
Uploaded Dataset /path/to/your/data/sample.json to /lepton-tuna/dataset/sample.json
```

#### Step 2: Verify Uploaded Data

To ensure the upload was successful, list the datasets stored in Tuna.

```bash
lep tuna list-data
```

**Output:**

```plaintext
/lepton-tuna/dataset
└── sample.json
0 directories, 1 file
```

#### Step 3: Train the Model

Next, initiate the training process for the model named `my-tuna-model`, using the `meta-llama/Meta-Llama-3-8B-Instruct` model and the uploaded dataset (`sample.json`). Specify the desired training parameters, such as epochs, batch size, and gradient accumulation.

```bash
lep tuna train --name my-tuna-model --resource-shape gpu.a10 --env HF_TOKEN=<your_hf_token> --model-path=meta-llama/Meta-Llama-3-8B-Instruct -dn=sample.json --num-train-epochs=2 --per-device-train-batch-size=16 --gradient-accumulation-steps=4 --learning-rate=0.0001 --lora --early-stop-threshold=0.01
```

**Output:**

```plaintext
Job tuna-my-tuna-model created successfully.
Model Training Job tuna-my-tuna-model for your model my-tuna-model created successfully.
```

#### Step 4: Monitor Training Progress

Check the status of your models to see if `my-tuna-model` is still in training or ready for use.

```bash
lep tuna list
```

**Output (during training):**

```plaintext
Tuna Models                                                                                         
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Name                                 ┃ Trained At                 ┃ Model                               ┃ Data        ┃ Lora or Medusa ┃ State    ┃ Deployments Name ┃ Train Job Name     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ my-tuna-model                        │ 2099-09-05T17:28:27.723254 │ meta-llama/Meta-Llama-3-8B-Instruct │ sample.json │ lora           │ Training │                  │ tuna-my-tuna-model │
└──────────────────────────────────────┴────────────────────────────┴─────────────────────────────────────┴─────────────┴────────────────┴──────────┴──────────────────┴────────────────────┘
```

Once the training is complete, the state will change to `Ready`.

```bash
lep tuna list
```

**Output (after training):**

```plaintext
Tuna Models                                                                                         
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Name                                 ┃ Trained At                 ┃ Model                               ┃ Data        ┃ Lora or Medusa ┃ State ┃ Deployments Name ┃ Train Job Name ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ my-tuna-model                        │ 2099-09-05T17:28:27.723254 │ meta-llama/Meta-Llama-3-8B-Instruct │ sample.json │ lora           │ Ready │                  │ Not Training   │
└──────────────────────────────────────┴────────────────────────────┴─────────────────────────────────────┴─────────────┴────────────────┴───────┴──────────────────┴────────────────┘
```

#### Step 5: Deploy the Model

Now that the model is ready, deploy it using the following command:

```bash
lep tuna run --name my-tuna-model --resource-shape gpu.a10
```

**Output:**

```plaintext
Running the most recent version of llm-by-lepton: llm-by-lepton-7v4vniao

Lepton is currently set to use a default timeout of 1 hour. This means that when there is no traffic for more than an hour, your deployment will automatically scale down to zero. This is to assist auto-release of unused debug deployments.
- If you would like to run a long-running photon (e.g. for production), set --no-traffic-timeout to 0.
- If you would like to turn off default timeout, set the environment variable LEPTON_DEFAULT_TIMEOUT=false.

Deployment created as tuna-my-tuna-model-0. Use `lep deployment status -n tuna-my-tuna-model-0` to check the status.
```

#### Summary

This example covers the entire workflow from data upload to model training and deployment. With a few simple commands, you're able to manage the full lifecycle of a machine learning model using Tuna, ensuring an efficient and clear process from start to finish.

---
## <span style="color:DeepSkyBlue">`Data` Management Commands
---
The `Data` commands provide seamless ways to manage your datasets within the Tuna platform. Whether it's listing, uploading, or removing data files, these commands offer you full control over your data.

### <span style="color:SkyBlue">`list-data` Command Overview

Need to check your available datasets? The `list-data` command lets you view all the data files currently stored in your Tuna environment.

#### Example Usage

```bash
lep tuna list-data
```

Here, the command lists all your data files, showing their names and details for quick verification.

### <span style="color:SkyBlue">`upload-data` Command Overview

The `upload-data` command makes it easy to upload new datasets to the Tuna platform. Simply point to your local file and assign a name, and you're good to go.

#### Example Usage

```bash
lep tuna upload-data --file <local_file_path> --name <data_file_name>
```

This uploads your data from the specified local path and names it in your Tuna environment for future reference.

### <span style="color:SkyBlue">`remove-data` Command Overview

Need to free up space or clean out old data? The `remove-data` command helps you delete specific datasets from the Tuna environment.

#### Example Usage

```bash
lep tuna remove-data --name <data_file_name>
```

Just specify the file name, and it's gone from your Tuna workspace. Simple and efficient.
		
---

## <span style="color:DeepSkyBlue">`Model` Management Commands
---
    
### <span style="color:SkyBlue">`train` Command Overview

Ready to fine-tune a machine learning model? The `train` command helps you configure and run training jobs with customizable options, from model configuration to training parameters.

#### Example Usage

```bash
lep tuna train -n my-tuna-model --resource-shape gpu.a10 --env HF_TOKEN=<your huggingface token> --model-path=meta-llama/Meta-Llama-3-8B-Instruct -dn=<file name you uploaded with upload-data> --num-train-epochs=2 --per-device-train-batch-size=16 --gradient-accumulation-steps=4 --learning-rate=0.0001 --lora --early-stop-threshold=0.01
```

In this example, you're training a model called "my-tuna-model" using your dataset and custom parameters like batch size and learning rate for optimized performance.

#### CLI Options

1. **`--name` / `-n`** (Required): `str`, Assigns a unique name for the tuna model being trained.  
2. **`--env` / `-e`**: `tuple`, Specifies environment variables to pass to the job, formatted as `NAME=VALUE`.  
3. **`--model-path`** (Required): `str`, Specifies the base model path for fine-tuning.  
4. **`--dataset-name` / `-dn`** (Required): `click.Path`, Path to the dataset used for training.  
5. **`--num-train-epochs`**: `int`, Default: `10`, Number of training epochs.  
6. **`--per-device-train-batch-size`**: `int`, Default: `32`, Training batch size per device (GPU or CPU).  
7. **`--gradient-accumulation-steps`**: `int`, Default: `1`, Number of gradient accumulation steps.  
8. **`--report-wandb`**: `flag`, Reports training metrics to Weights and Biases (wandb). Requires `WANDB_API_KEY`.  
9. **`--wandb-project`**: `str`, Specifies the wandb project, effective only when `--report-wandb` is set.  
10. **`--learning-rate`**: `float`, Default: `5e-5`, Specifies the learning rate for training.  
11. **`--warmup-ratio`**: `float`, Default: `0.1`, Specifies the warmup ratio for learning rate scheduling.  
12. **`--lora`**: `flag`, Enables LoRA for fine-tuning.  
13. **`--lora-rank`**: `int`, Default: `8`, Specifies the LoRA rank.  
14. **`--lora-alpha`**: `int`, Default: `16`, Specifies the alpha parameter for LoRA.  
15. **`--lora-dropout`**: `float`, Default: `0.1`, Specifies the dropout rate for LoRA.  
16. **`--medusa`**: `flag`, Trains Medusa heads instead of full model fine-tuning.  
17. **`--num-medusa-head`**: `int`, Default: `4`, Number of Medusa heads to train.  
18. **`--early-stop-threshold`**: `float`, Default: `0.01`, Stops training early if the reduction in validation loss is less than this threshold.  


### <span style="color:SkyBlue">`run` Command Overview

Once your model is trained, it’s time to deploy! The `run` command ensures the model is ready to go, checks its training status, and handles all the configurations necessary for a smooth deployment.

#### Example Usage

```bash
lep tuna run --name my-tuna-model --hf-transfer --tuna-step 5 --use-int --huggingface-token HUGGING_FACE_HUB_TOKEN --mount /path/to/storage:/mnt/storage
```

This runs the model "my-tuna-model" with GPU memory optimizations and faster Hugging Face transfer enabled for streamlined deployment.

#### CLI Options

1. **`--name` / `-n`** (Required): `str`, Name of the tuna model to deploy.  
2. **`--hf-transfer`**: `flag`, Default: `True`, Enables faster Hugging Face transfers.  
3. **`--tuna-step`**: `int`, Default: `3`, Minimum number of tokens to generate per chunk in streaming mode.  
4. **`--use-int`**: `flag`, Default: `True`, Applies quantization techniques to reduce GPU memory usage.  
5. **`--huggingface-token`**: `str`, Default: `"HUGGING_FACE_HUB_TOKEN"`, Specifies the Hugging Face token.  
6. **`--mount`**: `tuple`, Specifies persistent storage to be mounted in the format `STORAGE_PATH:MOUNT_PATH`.  


### <span style="color:SkyBlue">`list` Command Overview

Want a quick overview of your models? The `list` command displays all your models in either a table or list format, providing details like status, training date, data source, and any active deployments.

#### Example Usage

```bash
lep tuna list
```

By default, it displays your models in a table format. If you're on a small screen, switch to list view:

```bash
lep tuna list --list-view
```

#### CLI Options

1. **`--list-view` / `-l`**: Display models in a list format, perfect for smaller screens.

### <span style="color:SkyBlue">`remove` Command Overview

Need to delete a model? The `remove` command lets you safely remove a specified model after confirming its status and any active deployments.

#### Example Usage

```bash
lep tuna remove -n my-tuna-model
```

This removes the model "my-tuna-model" after verifying its existence and any dependencies.

### <span style="color:SkyBlue">`info` Command Overview

Curious about your model’s configuration? The `info` command retrieves all the relevant details for a specified model, helping you understand its current state.

#### Example Usage

```bash
lep tuna info -n my-tuna-model
```

It will print all the details related to "my-tuna-model" in an easy-to-read format.

### <span style="color:SkyBlue">`clear_failed_models` Command Overview

Cleaning up failed models is easy with the `clear_failed_models` command. It finds all models that failed during training and removes them along with any associated jobs.

#### Example Usage

```bash
lep tuna clear_failed_models
```

In this example, all models that encountered training failures are cleared, ensuring a clean workspace.