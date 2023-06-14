Photon
====

Photon is an open-source format for packaging Machine Learning models and applications. It supports various types of models and applications such as HuggingFace, PyTorch, ONNX etc. Each Photon consists of one `.photon` file, in zip format (which inside can contain multiple files), to capture all the necessary information, e.g. model_id, PyTorch state dict etc., to run the model or application anywhere. The structure inside the `.photon` file is pretty straightforward:

* ./metadata.json
    * e.g. {"name": "my-llm", "model": "hf:gpt2", "image": "lepton/photon:hf-runner"}
    * the information in metadata.json is pretty free-form currently, only "name", "model" and "image" are required. There are other optional fields like "requirements", "entrypoint" to further customize the environment or runtime behavior
* other resource files that need to be dynamically loaded at runtime
    * e.g. data/vocab.json - to customize vocabulary in a language model or application
