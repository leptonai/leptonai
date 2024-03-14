# ComfyUI API

ComfyUI API is setup for running comfyui workload with your choice of models, pipelines and configurations. This template will allow you to:

- Submit ComfyUI workflow_api.json as a job to run on the deployment.
- Cache the models for faster inference.
- Leverage persistent storage for storing and reusing the models.

This documentation will cover configurations including mount the storage and access it via API.

# Configurations

Here are few configurations you can change to suit your needs:

- Name: The name of your deployment, like `my-comfyui-api`
- Resource Shape : Resource used for running the workload. `gpu.a10` is recommended
- F