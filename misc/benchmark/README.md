This benchmark is a simplified version of the Ray LLMPerf library, which can
be found at the following address:

https://github.com/ray-project/llmperf

The code follows the standard Apache 2.0 license. To run the benchmark, you need to login in with lepton CLI first via `lep login` command then use following command to launch the benchmark test:
```
python run.py \
  --rounds 2 \
  --concur-requests 4 \
  --api-base "OPENAI_COMPATIBLE_API_BASE" \
  --api-key API_KEY \
  --model MODEL_NAME \
  --max-tokens=100
```

If you are benchmarking lepton endpoints and you are logged in, you can use `lep ws token` to obtain the workspace token.

To find the list of `OPENAI_COMPATIBLE_API_BASE` provided by Lepton AI, please refer to the [documentation page](https://www.lepton.ai/references/llm_models).
