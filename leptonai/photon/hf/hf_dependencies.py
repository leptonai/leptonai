"""
A manually maintained, best-effort map from HuggingFace (HF thereafter)
pipeline names to their corresponding dependencies.

LeptonAI SDK allows one to remotely run HF pipelines. However, there isn't a
standard way to pre-determine and install dependencies for HF pipelines yet.
Therefore, we manually maintain this map to install HF pipeline dependencies
when necessary, if you are launching the photon on the LeptonAI platform.

If you are running locally, you can install the missing packages with pip. We
intentionally do not automatically install the missing packages for you, as
some of the packages may be incompatible with your existing environment.

If you encounter missing packages dependencies for a HF pipeline, we appreciate
if you can send a PR to add the pipeline and its dependencies to this map.
"""

hf_pipeline_dependencies = {
    "baichuan-inc/Baichuan2-7B-Chat": ["bitsandbytes"],
    "microsoft/phi-1_5": ["einops"],
}

hf_no_attention_mask_models = {"microsoft/phi-1", "microsoft/phi-1_5"}
