import argparse
import os
from util import (
    request_chat_completion,
    write_json_file,
    read_json_file,
    validate_input_dataset,
    add_http_if_not_exist,
    show_table,
    show_bar_chart,
    show_tree,
)
import logging
import copy
from rich.progress import Progress
import threading
from functools import partial
import json
import numpy as np
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

OPENAI_BASE = os.getenv("OPENAI_BASE") or "https://api.openai.com"


class LLM:
    server_address: str  # OpenAI API Server
    model_name: str

    def __init__(self, model_name, server_address, max_tokens, evaluator, alias=None):
        self.model_name = model_name
        self.server_address = server_address
        # Separated module for openai
        self.api_base = f"{server_address}"
        self.api_key = "APIKEY"
        self.max_tokens = max_tokens
        self.evaluator = evaluator
        self.alias = alias if alias is not None else model_name
        self.dataset = None
        self.single_scores = []

    def generate_answer(self, dataset, callback):
        dataset = copy.deepcopy(dataset)
        for i in range(len(dataset)):
            item = dataset[i]
            messages = item["messages"]
            assist_idxs = [
                i for i in range(len(messages)) if messages[i]["role"] == "assistant"
            ]
            for idx in assist_idxs:
                while True:
                    done = False
                    try:
                        completion = request_chat_completion(
                            messages[:idx],
                            self.model_name,
                            self.api_base,
                            os.getenv("OPENAI_KEY"),
                            kwargs={
                                "max_tokens": self.max_tokens,
                                "temperature": 0.1,  # TODO:cjx?
                            },
                        )
                        # Overwrite assistant message
                        messages[idx]["content"] = completion["content"]
                        done = True
                    except Exception as e:
                        logging.error(e)
                        time.sleep(0.5)
                    if done:
                        break
            callback(i + 1)
        self.dataset = dataset

    def eval_single(self, dataset, callback):
        if self.dataset:
            dataset = copy.deepcopy(self.dataset)
        for i in range(len(dataset)):
            item = dataset[i]
            messages = item["messages"]
            assist_idxs = [
                i for i in range(len(messages)) if messages[i]["role"] == "assistant"
            ]
            for idx in assist_idxs:
                while True:
                    done = False
                    try:
                        completion = request_chat_completion(
                            [
                                {
                                    "role": "user",
                                    "content": f"""Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. Begin your evaluation by providing a short explanation. Be as objective as possible. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: \"[[rating]]\", for example: \"Rating: [[5]]\”
        Here is the dilalog, please only evaluate on the LAST answer:
        ```json
        {json.dumps(messages[:idx + 1], ensure_ascii=False, indent=4)}
        ```
        """,
                                },
                            ],
                            model=self.evaluator,
                            base=OPENAI_BASE,
                            key=os.getenv("OPENAI_KEY"),
                            kwargs={
                                "functions": [
                                    {
                                        "name": "parse_eval_lepton",
                                        "description": (
                                            "Make evaluation call with explaination and"
                                            " score."
                                        ),
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "eval_explain": {
                                                    "type": "string",
                                                    "description": (
                                                        "Litral evaluation and"
                                                        " explaination."
                                                    ),
                                                },
                                                "score": {
                                                    "type": "number",
                                                    "description": "Score between 0-10",
                                                },
                                            },
                                            "required": ["eval_explain", "score"],
                                        },
                                    }
                                ],
                                "function_call": {"name": "parse_eval_lepton"},
                                "max_tokens": self.max_tokens,
                                "temperature": 0.5,
                            },
                        )

                        eval_str = completion["function_call"].get("arguments")

                        self.single_scores.append(json.loads(eval_str)["score"])

                        evals = messages[idx].get("eval", [])
                        evals.append(eval_str)
                        messages[idx]["eval"] = json.loads(eval_str)
                        done = True
                    except Exception as e:
                        logging.error(e)
                        time.sleep(0.5)
                    if done:
                        break
            callback(i + 1)
        self.dataset = dataset

    def save(self, dir):
        if self.dataset:
            write_json_file(
                self.dataset, os.path.join(dir, f"{self.alias}-eval-singlewise.json")
            )


class LLMPair:
    def __init__(self, llm_1, llm_2, evaluator, max_tokens=1024):
        self.llm_1 = llm_1
        self.llm_2 = llm_2
        self.max_tokens = max_tokens
        self.evaluator = evaluator
        self.valid = self.validate_pairwise()
        self.metadata = {
            "model_A": {"name": self.llm_1.alias, "data": self.llm_1.dataset},
            "model_B": {"name": self.llm_2.alias, "data": self.llm_2.dataset},
            "pairwise_eval": [],
            "vote_A": 0,
            "vote_B": 0,
        }
        if self.valid:
            logging.info(
                f"Data validation passes for pairwise {llm_1.alias} and {llm_2.alias}"
            )

    def win_tree(self):
        if self.metadata["vote_A"] > self.metadata["vote_B"]:
            return [f"{self.llm_1.alias}🏆", f"{self.llm_2.alias}"]
        elif self.metadata["vote_A"] == self.metadata["vote_B"]:
            return [f"{self.llm_1.alias}🤝", f"{self.llm_2.alias}🤝"]
        else:
            return [f"{self.llm_1.alias}", f"{self.llm_2.alias}🏆"]

    def validate_pairwise(self):
        if len(self.llm_1.dataset) != len(self.llm_2.dataset):
            logging.error("Pairwise data count mismatches.")
            return False
        for left, right in zip(self.llm_1.dataset, self.llm_2.dataset):
            msg_l = left["messages"]
            msg_r = right["messages"]
            for conv_l, conv_r in zip(msg_l, msg_r):
                if conv_l["role"] != conv_r["role"]:
                    logging.error("Pairwise data role mismatches.")
                    return False
                elif (
                    conv_l["role"] != "assistant"
                    and conv_l["content"] != conv_r["content"]
                ):
                    logging.error("Pairwise data content mismatches.")
                    return False
        return True

    def eval(self, dataset, callback):
        dataset_l = copy.deepcopy(self.llm_1.dataset)
        dataset_r = copy.deepcopy(self.llm_2.dataset)

        for i in range(len(dataset_l)):
            item_l = dataset_l[i]
            item_r = dataset_r[i]
            messages_l = item_l["messages"]
            messages_r = item_r["messages"]
            assist_idxs = [
                i
                for i in range(len(messages_l))
                if messages_l[i]["role"] == "assistant"
            ]
            for idx in assist_idxs:
                # Remove `eval` field from single-wise eval for impartial judgement
                msg_l = messages_l[idx]
                msg_r = messages_r[idx]
                if msg_l.get("eval") is not None:
                    del msg_l["eval"]
                if msg_r.get("eval") is not None:
                    del msg_r["eval"]

            evals_data = []
            for idx in assist_idxs:
                while True:
                    done = False
                    try:
                        completion = request_chat_completion(
                            [
                                {
                                    "role": "system",
                                    "content": """Please act as an impartial judge and evaluate the quality of the responses provided by two AI assistants to the user question displayed below. You should choose the assistant that follows the user's instructions and answers the user's question better. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of their responses. Begin your evaluation by comparing the two responses and provide a short explanation. Avoid any position biases and ensure that the order in which the responses were presented does not influence your decision. Do not allow the length of the responses to influence your evaluation. Do not favor certain names of the assistants. Be as objective as possible. After providing your explanation, output your final verdict by strictly following this format: \"[[A]]\" if assistant A is better, \"[[B]]\" if assistant B is better, and \"[[C]]\" for a tie.”.

IMPORTANT: Please ONLY evaluate on the last answer from both conversation.""",
                                },
                                {
                                    "role": "user",
                                    "content": f"""
BEGINNING of convseration between user and Assistant A
```json
{json.dumps(messages_l[:idx + 1], ensure_ascii=False, indent=4)}
```
END of convseration between user and Assistant A

BEGINNING of convseration between user and Assistant B
```json
{json.dumps(messages_r[:idx + 1], ensure_ascii=False, indent=4)}
```
END of convseration between user and Assistant B
""",
                                },
                            ],
                            model=self.evaluator,
                            base=OPENAI_BASE,
                            key=os.getenv("OPENAI_KEY"),
                            kwargs={
                                "functions": [
                                    {
                                        "name": "parse_eval_lepton",
                                        "description": (
                                            "Make evaluation call with explaination and"
                                            " vote."
                                        ),
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "eval_explain": {
                                                    "type": "string",
                                                    "description": (
                                                        "Litral evaluation and"
                                                        " explaination."
                                                    ),
                                                },
                                                "vote": {
                                                    "type": "string",
                                                    "enum": ["A", "B", "C"],
                                                    "description": (
                                                        "Select `A` if Assistant A"
                                                        " performs better or Select `B`"
                                                        " if Assistant B performs"
                                                        " better, otherwise select `C`"
                                                        " for a tie."
                                                    ),
                                                },
                                            },
                                            "required": ["eval_explain", "vote"],
                                        },
                                    }
                                ],
                                "function_call": {"name": "parse_eval_lepton"},
                                "max_tokens": self.max_tokens,
                                "temperature": 0.5,
                            },
                        )

                        eval_str = completion["function_call"].get("arguments")
                        vote = json.loads(eval_str)["vote"]
                        if vote == "A":
                            self.metadata["vote_A"] += 1
                        elif vote == "B":
                            self.metadata["vote_B"] += 1
                        elif vote == "C":
                            self.metadata["vote_A"] += 0.5
                            self.metadata["vote_B"] += 0.5
                        else:
                            raise ValueError(f"Invalid vote: {vote} from evaluation.")
                        evals_data.append(json.loads(eval_str))
                        done = True
                    except Exception as e:
                        logging.error(e)
                        time.sleep(0.5)
                    if done:
                        break
            self.metadata["pairwise_eval"].append(evals_data)
            callback(i + 1)

    def save(self, dir):
        if self.metadata:
            write_json_file(
                self.metadata,
                os.path.join(
                    dir, f"{self.llm_1.alias}&{self.llm_2.alias}-eval-pairwise.json"
                ),
            )


def main():
    parser = argparse.ArgumentParser(description="Evaluator for tuna @ v1.0")
    parser.add_argument(
        "--tuna-api-addresses",
        type=str,
        help="OpenAI API addresses of tuna model service, separated by ','.",
        required=True,
    )
    parser.add_argument("--dataset", type=str, help="Question dataset.", required=True)
    parser.add_argument(
        "--output-dir", type=str, help="Output dir for generating files", required=True
    )
    parser.add_argument(
        "--add-gpt-3",
        action="store_true",
        help="Generate answers from gpt-3.5-turbo if true",
    )
    parser.add_argument(
        "--add-gpt-4", action="store_true", help="Generate answers from gpt-4 if true"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=1024, help="Max tokens to be generated."
    )
    parser.add_argument(
        "--evaluator",
        type=str,
        default="gpt-3.5-turbo-16k",
        choices=["gpt-4", "gpt-3.5-turbo-16k"],
        help="Default evaluator to use. Support `gpt-4` and `gpt-3.5-turbo-16k`",
    )

    args = parser.parse_args()

    if os.getenv("OPENAI_KEY") is None:
        logging.error("`OPENAI_KEY` is not set as env var.")
        return
    if not os.path.isfile(args.dataset):
        logging.error(f"dataset: {args.dataset} is missing.")
        return

    dataset = read_json_file(args.dataset)
    try:
        validate_input_dataset(dataset)
    except ValueError as e:
        logging.error(e)
        return

    model_to_addr = {}
    # http://xxxxx^alias_name@model_name
    tuna_addresses = args.tuna_api_addresses.split(",")

    for addr in tuna_addresses:
        host = addr.split("^")[0]
        host = add_http_if_not_exist(host)
        alias, model_name = addr.split("^")[1].split("@")
        model_to_addr.update({alias: (host, model_name)})
    if args.add_gpt_3:
        model_to_addr.update({"gpt-3.5-turbo-16k": (OPENAI_BASE, "gpt-3.5-turbo-16k")})
    if args.add_gpt_4:
        model_to_addr.update({"gpt-4": (OPENAI_BASE, "gpt-4")})

    show_table(
        ["Model Alias", "API Address", "Max tokens"],
        [
            [x, f"{model_to_addr[x][0]} : {model_to_addr[x][1]}", str(args.max_tokens)]
            for x in model_to_addr
        ],
        [{}, {}, {"justify": "right"}],
    )

    llms = [
        LLM(
            model_to_addr[k][1],
            model_to_addr[k][0],
            args.max_tokens,
            alias=k,
            evaluator=args.evaluator,
        )
        for k in model_to_addr
    ]

    from itertools import cycle

    colors = cycle(["cyan", "magenta", "green", "yellow", "blue", "red"])

    with Progress() as progress:
        tasks = [
            progress.add_task(
                f"[{next(colors)}]Generation for {llm.alias}...", total=len(dataset)
            )
            for llm in llms
        ]

        idx = 0
        threads = []
        for llm in llms:

            def callback(n_finished, index):
                progress.update(tasks[index], completed=n_finished)

            thread = threading.Thread(
                target=llm.generate_answer, args=(dataset, partial(callback, index=idx))
            )
            thread.start()
            idx += 1
            threads.append(thread)
        for t in threads:
            t.join()

    with Progress() as progress:
        tasks = [
            progress.add_task(
                f"[{next(colors)}]Evaluation (Single-wise) for {llm.alias}...",
                total=len(dataset),
            )
            for llm in llms
        ]

        idx = 0
        threads = []
        for llm in llms:

            def callback(n_finished, index):
                progress.update(tasks[index], completed=n_finished)

            thread = threading.Thread(
                target=llm.eval_single, args=(dataset, partial(callback, index=idx))
            )
            thread.start()
            idx += 1
            threads.append(thread)
        for t in threads:
            t.join()
    # for llm in llms:
    #     llm.save(args.output_dir)

    show_bar_chart(
        {llm.alias: np.mean(np.array(llm.single_scores)) for llm in llms},
        "Average score out of 10",
    )

    pair_count = 0
    valid_pairs = []
    for i in range(len(llms)):
        for j in range(i + 1, len(llms)):
            pair = LLMPair(
                llms[i], llms[j], evaluator=args.evaluator, max_tokens=args.max_tokens
            )
            if pair.valid:
                valid_pairs.append([pair_count, pair])
                pair_count += 1
    tree_payload = {
        f"#{v[0]}": [v[1].llm_1.alias, v[1].llm_2.alias] for v in valid_pairs
    }
    show_tree("Pairwise evaluation is ready for following groups:", tree_payload)

    selected_idxs = np.arange(0, pair_count).tolist()
    # eval_all = ask_yes_no("Do you want to evaluate all of these groups?")
    # if not eval_all:
    #     while True:
    #         done = True
    #         selected_idxs = ask_for_numbers(f"Input the group number needed to be evaluated separated by commas:")
    #         selected_idxs = list(set(selected_idxs))
    #         for x in selected_idxs:
    #             if x >= pair_count or x < 0:
    #                 logging.error(f'Invalid group number: {x}.')
    #                 done = False
    #         if done:
    #             break
    # logging.info(f'Group: {selected_idxs} is selected to be evaluated.')

    valid_pairs = [
        valid_pairs[i][1] for i in range(len(valid_pairs)) if i in selected_idxs
    ]
    with Progress() as progress:
        tasks = [
            progress.add_task(
                f"[{next(colors)}]Evaluation (Pair-wise) for"
                f" {llm_pair.llm_1.alias} & {llm_pair.llm_2.alias}...",
                total=len(dataset),
            )
            for llm_pair in valid_pairs
        ]

        idx = 0
        threads = []
        for llm_pair in valid_pairs:

            def callback(n_finished, index):
                progress.update(tasks[index], completed=n_finished)

            thread = threading.Thread(
                target=llm_pair.eval, args=(None, partial(callback, index=idx))
            )
            thread.start()
            idx += 1
            threads.append(thread)
        for t in threads:
            t.join()

    tree_payload = {f"#{i}": valid_pairs[i].win_tree() for i in range(len(valid_pairs))}
    show_tree("Pairwise evaluation result:", tree_payload)
    for llm_pair in valid_pairs:
        llm_pair.save(args.output_dir)


if __name__ == "__main__":
    main()
