import argparse
import os
import json
import random
import operator
from collections import OrderedDict
import math
import aiohttp
import asyncio
from loguru import logger
from tqdm import tqdm

OPENAI_HOMEBREW_PROMPT = """You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2021-09
Current date: 2023-07-07
"""


async def augment(sample, session, n_gen_per_request=1):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_KEY')}",
    }
    ref_messages = sample["messages"]
    for i in range(len(ref_messages)):
        ref_messages[i] = OrderedDict(
            sorted(ref_messages[i].items(), key=operator.itemgetter(0), reverse=True)
        )

    messages = [
        {"role": "system", "content": OPENAI_HOMEBREW_PROMPT},
        {
            "role": "user",
            "content": (
                f"""```json
{json.dumps(ref_messages, ensure_ascii=False, indent=0)}
```"""
                + """

This is a dataset for LLM SFT.
Please do following steps:
1. Explain what this dataset is used for.
2. If we need to augment this dataset, how could we generalize into other scenerios. Please list what we could modify and what we couldn’t during this augmentation process.
3. Upon your reply to step 2 , please generate such a NEW and COMPLETE json example which conforms to the requirements listed above. 

Requirements for generation:
1. If there is a `system` content at the begining, please also imitate this behavior.
2. If there are few-shot examples inside prompt, please also include these examples.
3. dataset generated must be valid json object
"""
            ),
        },
    ]

    data = {
        "model": args.model,
        "messages": messages,
        "max_tokens": 10000,
        "temperature": 0.8,
        "top_p": 0.95,
        "n": n_gen_per_request,
    }
    async with session.post(
        f"{os.getenv('OPENAI_BASE', 'https://api.openai.com')}/v1/chat/completions",
        json=data,
        headers=headers,
    ) as response:
        results = []
        try:
            ret = await response.json()
            if ret.get("choices", []) == []:
                logger.error(f"OpenAI API error: {ret}")
                return results
            for choice in ret.get("choices", []):
                ret_msg = choice.get("message", {}).get("content", "")
                # Try parsing json inside
                occurs = find_all_occurrences(ret_msg, "```")
                if len(occurs) < 2:
                    logger.error("Invalid json found and skipped.")
                    print(ret)
                    continue
                else:
                    substr = ret_msg[int(occurs[0]) : int(occurs[-1])]
                    beg = find_all_occurrences(substr, "[")
                    if len(beg) > 0:
                        substr = substr[beg[0] :]
                    parsed_json = json.loads(substr)
                    results.append(parsed_json)
            return results
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for parsing, error: {e}")
            return results
        except Exception as e:
            logger.error(f"Unknown error: {e}")
            return results


async def batch_augment(samples, n_gen_per_request):
    async with aiohttp.ClientSession() as session:
        tasks = [augment(sample, session, n_gen_per_request) for sample in samples]
        return await asyncio.gather(*tasks)


def find_all_occurrences(text, substring):
    occurrences = []
    start_index = 0

    while True:
        index = text.find(substring, start_index)
        if index == -1:
            break
        occurrences.append(int(index))
        start_index = index + 1
    return occurrences


async def main(args):
    if os.getenv("OPENAI_KEY") is None:
        raise ValueError("`OPENAI_KEY` is not set as ENV VAR.")
    try:
        with open(args.sample_file_path, "r") as file:
            sample_data = json.load(file)
    except FileNotFoundError:
        logger.error(f"File {args.sample_file_path} not found.")
        return

    json_results = []
    n_gen_per_request = 5

    n_batch = int(math.ceil((args.n_new_sample / n_gen_per_request) / args.rare_rpm))

    with tqdm(total=n_batch, desc="Generating progress") as pbar:
        for i in range(n_batch):
            # Randomly sample from the dataset for generation reference.
            batch_results = await batch_augment(
                random.sample(sample_data, args.rare_rpm), n_gen_per_request
            )
            for batch_result in batch_results:
                json_results.extend(batch_result)
            pbar.update(i + 1)

    logger.info(f"{len(json_results)} new samples are generated.")

    # Write to file
    with open(args.output_path, "w") as json_file:
        json.dump(json_results, json_file, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data augmentation for lepton @ v1.0")

    parser.add_argument(
        "--n_new_sample",
        type=int,
        default=1000,
        help="Number of max samples to be generated.",
        required=False,
    )
    parser.add_argument(
        "--rare_rpm",
        type=int,
        default=3,
        help="Max request per minute limited by OpenAI.",
        required=False,
    )
    parser.add_argument(
        "--model", type=str, default="gpt-3.5-turbo-16k-0613", required=False
    )
    parser.add_argument("--output_path", type=str, required=True)
    parser.add_argument(
        "--sample_file_path",
        type=str,
        help="Sample training data for augmentation reference.",
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args))
