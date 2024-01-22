import asyncio
import argparse
from collections import Counter
import os
import queue
import re
import random
import sys
import threading
import time

import openai
from num2words import num2words
import pandas as pd
from transformers import LlamaTokenizerFast

os.environ["TOKENIZERS_PARALLELISM"] = "true"

tokenizer = LlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")


def rnd_num_generator(num_digits=3) -> str:
    # Step 1: Generate a random number
    # Generate the number of digits specified (e.g. if NUM_DIGITS = 3, then
    # any number between 100 and 1000 is OK).
    rnd_num = random.randrange(10 ** (num_digits - 1), 10 ** (num_digits))

    # Step 2: convert to words.
    rnd_num_words = num2words(rnd_num)

    return rnd_num, rnd_num_words


async def endpoint_evaluation_request(client, ep_config):
    if args.validate:
        rnd_num, rnd_num_words = rnd_num_generator(args.num_digits)
        prompt = (
            "Convert the following sequence of words into a number:"
            f" {rnd_num_words}.\nPrint the number first, then tell me a very long"
            " story."
        )
    elif ep_config["prompt_file"]:
        with open(ep_config["prompt_file"], "r") as fid:
            rnd_num = None
            prompt = fid.read()
    else:
        rnd_num = None
        prompt = ep_config["prompt"]

    tokens_in = len(tokenizer.encode(prompt))
    words = ""

    messages = [
        {"role": "user", "content": prompt},
    ]
    try:
        st = time.time()
        ttft = None
        response = await client.chat.completions.create(
            model=ep_config["model"],
            messages=messages,
            max_tokens=args.max_tokens,
            # Please keep temp at 0. Otherwise increases the number of mismatches.
            temperature=0,
            # Do not set to false. You will get bogus results.
            stream=True,
        )
        async for tok in response:
            if not tok.choices:
                continue
            delta = tok.choices[0].delta
            if ttft is None and (delta.role or delta.content):
                ttft = time.time() - st
            if delta.content:
                words += tok.choices[0].delta.content
        et = time.time()
    except Exception as e:
        return ("Exception", -1, -1, -1, -1, str(e))

    # Get rid of commas.
    tokens_out = len(tokenizer.encode(words))
    if args.validate:
        nums = re.findall(r"\d+", words)
        if len(nums) > 0:
            retval = int(nums[0])
            valid = "OK"
            cause = ""
            if retval != rnd_num:
                valid = "Mismatch"
                cause = f"input: {rnd_num_words}, expect: {rnd_num}, got: {retval}"
        else:
            valid = "Mismatch"
            cause = f"Output unparseable. Input = {rnd_num}. Output:\n {words}"
    else:
        valid = "OK"
        cause = ""
    return (valid, ttft, et - st, tokens_in, tokens_out, cause)


async def endpoint_evaluation_round(client, concur_requests, ep_config):
    results = await asyncio.gather(*(
        endpoint_evaluation_request(client, ep_config) for _ in range(concur_requests)
    ))
    return results


def endpoint_evaluation_qps(client, ep_config, results_queue, stop_event):
    loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    threading.Thread(target=run_loop).start()

    time_between_requests = 1 / args.qps

    def task_done_callback(task):
        results_queue.put(task.result())

    while True:
        if stop_event.is_set():
            print("stop event received, stopping loop")
            loop.call_soon_threadsafe(loop.stop)
            return

        st = time.time()
        future = asyncio.run_coroutine_threadsafe(
            endpoint_evaluation_request(client, ep_config), loop
        )
        future.add_done_callback(task_done_callback)
        et = time.time()
        tosleep = time_between_requests - (et - st)
        if tosleep > 0:
            time.sleep(tosleep)

    return results_queue


def endpoint_evaluation(ep_config):
    client = openai.AsyncOpenAI(
        base_url=ep_config["api_base"], api_key=ep_config["api_key"]
    )

    if args.qps is not None:
        query_results = []
        elts = []
        results_queue = queue.Queue()
        stop_event = threading.Event()
        threading.Thread(
            target=endpoint_evaluation_qps,
            args=(client, ep_config, results_queue, stop_event),
        ).start()

        st = time.time()
        try:
            while True:
                try:
                    result = results_queue.get(timeout=0.1)
                    query_results.append(result)
                    if len(query_results) % args.qps == 0:
                        et = time.time()
                        elts.append(et - st)
                        st = et
                    if len(query_results) % (5 * args.qps) == 0:
                        results_analysis(query_results, elts)
                        query_results = []
                        elts = []
                except queue.Empty:
                    pass
        finally:
            stop_event.set()
    else:
        loop = asyncio.get_event_loop()

        for concur_requests in args.concur_requests:
            query_results = []
            elts = []
            for _ in range(args.rounds):
                st = time.time()
                results = loop.run_until_complete(
                    endpoint_evaluation_round(client, concur_requests, ep_config)
                )
                query_results.extend(results)
                et = time.time()
                elt = et - st
                elts.append(elt)
                tosleep = args.sleep - elt
                if tosleep > 0:
                    print("Sleeping for %.4f seconds" % tosleep)
                    time.sleep(tosleep)
            results_analysis(query_results, elts, concur_requests)


def results_analysis(query_results, elts, concur_requests=None):
    print("---- Results analysis ----")
    if concur_requests:
        print(f"Concurrency: {concur_requests}")
    df = pd.DataFrame(
        query_results,
        columns=[
            "valid",
            "ttft",
            "total_time",
            "tokens_in",
            "tokens_out",
            "cause",
        ],
    )
    cdf = df[df.valid != "Exception"].copy()
    if len(cdf) > 0:
        total_out_tokens_per_s = cdf.tokens_out.sum().sum() / sum(elts)
        cdf["out_tokens_per_s"] = cdf.tokens_out / cdf.total_time
        cdf["inter_tokens_delay"] = cdf.total_time / cdf.tokens_out
        mean_tokens_in = int(cdf["tokens_in"].mean())
        mean_tokens_out = int(cdf["tokens_out"].mean())
        mean_ttft = cdf["ttft"].mean()
        min_ttft = cdf["ttft"].min()
        max_ttft = cdf["ttft"].max()
        gt_3_ttft = len(cdf[cdf["ttft"] > 3]) / len(cdf)
        print(
            "Execution time:"
            f"\n  mean (per request): {cdf.total_time.mean():.2f} s"
            f"\n  mean (per round): {sum(elts)/len(elts):.2f} s"
            f"\n  total: {sum(elts):.2f} s"
        )
        print(
            "Throughput:"
            f"\n  mean (per request): {cdf.out_tokens_per_s.mean():.2f} token/s"
            f"\n  total: {total_out_tokens_per_s:.2f} token/s"
        )
        print(f"Latency:\n  mean: {cdf.inter_tokens_delay.mean()*1000:.2f} ms/token")
        print(
            "TTFT:"
            f"\n  mean: {mean_ttft*1000:.0f} ms"
            f"\n  min: {min_ttft*1000:.0f} ms"
            f"\n  max: {max_ttft*1000:.0f} ms"
            f"\n  > 3 s: {gt_3_ttft*100:.2f}%"
        )
        print(f"Mean #tokens:\n  input: {mean_tokens_in}\n  output: {mean_tokens_out}")

    def error_analysis(df):
        # Group exceptions based on exceptions cause
        if args.validate:
            exceptions = df[df.valid.isin(["Mismatch", "Exception"])]
        else:
            exceptions = df[df.valid == "Exception"]
        exceptions_by_cause = Counter()
        # Ideally we should group by some error code
        for cause in exceptions["cause"]:
            exceptions_by_cause[cause] += 1

        if exceptions_by_cause:
            print("Exceptions by cause:")
            for cause, count in exceptions_by_cause.items():
                print(f" - {count}: {cause}")

    error_analysis(df)
    print("-------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="meta-llama/Llama-2-70b-chat-hf",
        help="model name",
    )
    parser.add_argument(
        "--num-digits", type=int, default=3, help="number of digits for mismatch search"
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="sleep between rounds of requests (to deal with rate limiting)",
    )
    parser.add_argument(
        "-c",
        "--concur-requests",
        default="10",
        help="number of concurrent requests, use comma to separate multiple values",
    )
    parser.add_argument(
        "-r", "--rounds", type=int, default=4, help="number of rounds of requests"
    )
    parser.add_argument(
        "-q",
        "--qps",
        type=int,
        default=None,
        help=(
            "number of requests per second. if set, overrides --concur-requests and"
            " --rounds"
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=384,
        help="Upper limit on the number of returned tokens to prevent 'runaway LLMs'.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=117,
        help="Random seed to standardize results. By default fully random.",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default="http://localhost:8080/v1/",
        help="API base url",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="a" * 32,
        help="API key",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Whether to validate the results",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="tell me a very long story.",
        help="User prompt to send to the model",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default="",
        help=(
            "If set, the file that contains the prompt text. Prompt file takes"
            " precedence over prompt."
        ),
    )
    args = parser.parse_args()
    endpoint_config = {}
    if args.random_seed >= 0:
        random.seed(args.random_seed)
    endpoint_config["api_base"] = args.api_base
    endpoint_config["api_key"] = args.api_key
    endpoint_config["model"] = args.model
    endpoint_config["prompt"] = args.prompt
    endpoint_config["prompt_file"] = args.prompt_file

    concur_requests = []
    for c in args.concur_requests.split(","):
        try:
            c_int = int(c)
        except ValueError:
            print(f"concurent requests must be integers, got {c}")
            sys.exit(1)

        if c_int <= 0:
            print(f"concurent requests must be positive integers, got {c}")
            sys.exit(1)

        concur_requests.append(c_int)

    args.concur_requests = concur_requests

    # Endpoint evaluation
    endpoint_evaluation(endpoint_config)
