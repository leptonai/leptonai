# Universal Tokenizer

The Universal tokenizer is a utility photon that allows one to pass in a model name from huggingface and a piece of text (or a list of texts) to get the tokenized outputs and/or the length of the tokenized outputs. It is intended to be used in cases where one wants to do a simple bookkeeping of tokens processed, but does not want to load the models fully.

The photon tries its best to load tokenizers, but since huggingface tokenizer can contain arbitrary code (which introduces additional dependencies), some of them might not work. If you believe a model is commonly used and should be included, please contact us at [info@lepton.ai](mailto:info@lepton.ai).

# Configurations

You only need to set the following environmental variables to launch the tokenizer:

* `TRUST_REMOTE_CODE`: whether to trust remote code contained in the huggingface model repo. This is needed in many models that ship with custom tokenizers. If you would like to make sure none of remote code is executed, set this to `false`. Default true.

This deployment may also require the following secret(s) to run:

* `HUGGING_FACE_HUB_TOKEN`: (Optional) the token to access the Hugging Face model hub. You can create one or find your existing token at [the hf settings page](https://huggingface.co/settings/tokens).

Once these fields are set, click `Deploy` button at the bottom of the page to create the deployment. You can see the deployment has now been created under [Deployments](https://dashboard.lepton.ai/workspace-redirect/deployments).
