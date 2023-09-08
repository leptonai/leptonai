# Tuna Augmentor
Augment your dataset for tuna via `ChatGPT`;

## Brief
This tool is primarily intended for enhancing the dataset used in tuna training. It caters to the following scenarios:

1. Tone Mimicry: It can replicate the tone of both the user and assistant.
2. Pattern Mimicry: Operating akin to few-shot learning, this tool can produce data samples that follow a similar structure to the provided source samples. This is particularly beneficial for patterns found in `json` and other structured formats.

However, it's worth noting that this tool is not designed to expand domain knowledge through generation, as the accuracy and reliability of such an approach cannot be guaranteed.

## Usage
1. Set ENV-VARs:
    - `OPENAI_KEY`: Your openai secret key
    - `OPENAI_BASE`: (Optional) API Base for OPENAI Official Server, default to https://api.openai.com

2. Execution:
```shell
python ./augment.py --n_new_sample 50 --output_path ./augment_data-2.json --sample_file_path ./dataset.json
```
- `n_new_sample`: How many samples to be generated;
- `output_path`: Output file path;
- `sample_file_path`: Dataset to refer to for generation;



