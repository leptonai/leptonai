This benchmark is a simplified version of the Ray LLMPerf library, which can
be found at the following address:

https://github.com/ray-project/llmperf

The code follows the standard Apache 2.0 license. To run the benchmark, you need to login in with lepton CLI first via `lep login` command then use following command to launch the benchmark test:
```
python run.py --rounds 1 --concur-requests 50 --api-base "https://llama2-70b.lepton.run/api/v1/" --api-key `lep ws token` -m llama2-70b --max-tokens=100;
```

For more models, please refer to the [documentation page](https://www.lepton.ai/references/llm_models).
