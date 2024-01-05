<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/vllm-project/vllm/main/docs/source/assets/logos/vllm-logo-text-dark.png">
    <img alt="vLLM" src="https://raw.githubusercontent.com/vllm-project/vllm/main/docs/source/assets/logos/vllm-logo-text-light.png" width=55%>
  </picture>
</p>

# vLLM

vLLM is an easy, fast, and cheap LLM serving for everyone, developed by the University of California, Berkeley. For more details, check out the [github page](https://github.com/vllm-project/vllm/).

Lepton provides a turnkey deployment of vLLM, which you can use to serve your own LLM models.

This is an OpenAI API compatible deployment. You can use it as a drop-in replacement for the OpenAI API. For more details, check out the vLLM [documentation](https://docs.vllm.ai/en/latest/getting_started/quickstart.html#using-openai-chat-api-with-vllm).

# Configurations

Most likely, you will need a GPU resource shape to run models.

To customize the deployment, you can set the following environmental variables.

* `VLLM_MODEL`: The model name to run. The supported models are listed [here](https://docs.vllm.ai/en/latest/models/supported_models.html).
* `VLLM_MODEL_NAME`: the model name to be used in the api server.
* `VLLM_MODEL_REVISION`: the model revision to be used in the api server.
* `VLLM_TENSOR_PARALLEL_SIZE`: the tensor parallel size to be used. Note that this is also constrained by the number of GPUs available.
* `VLLM_USE_MODELSCOPE`: whether to load model from ModelScope. If set to `False`, the model will be loaded from Hugging Face model hub.
* `VLLM_TRUST_REMOTE_CODE`: whether to trust remote code. If set to `False`, remote code won't be trusted.

This deployment may also requires the following secrets to run:

* `HUGGING_FACE_HUB_TOKEN`: the token to access the Hugging Face model hub. You can create one or find your existing token at [the hf settings page](https://huggingface.co/settings/tokens).

# Notes

The vLLM logo, name, and other assets are owned by the vLLM project under the Apache 2.0 license. For more details, check out the [vLLM github page](https://github.com/vllm-project/vllm/).