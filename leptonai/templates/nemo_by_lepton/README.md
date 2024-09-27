# NeMO

Nvidia NeMo (Neural Modules) is an open-source toolkit designed to help developers build, train, and fine-tune large-scale AI models, especially those related to speech, language, and text processing. For more details, check out the [github page](https://github.com/NVIDIA/NeMo).

# Configurations

This deployment will require a GPU. As a result, make sure you use a GPU resource shape.

To customize the deployment, you can set the following environmental variables.
* `NEMO_MODEL`: the model to run, such as "nvidia/canary-1b." Note that depending on the specific model being used, the arguments to the `transcribe()` function may change - feel free to adjust this Photon to your specific use case.

# Example Usage

```python
import requests

url = 'https://{WORKSPACE_NAME}-{DEPLOYMENT_NAME}.tin.lepton.run/transcribe_audio'

headers = {
    'Authorization': f'Bearer {API_KEY}'
}

file_path = "test.wav"
# Open the file in binary mode
with open(file_path, "rb") as f:
    # Make a POST request with the file
    files = {"file": f}
    response = requests.post(url, headers=headers, files=files)

# Print out the server's response
print("Transcription:", response.json())
```

## Output

Calling the above endpoint as is will give the following response:
```
[
    "Today is a beautiful day, I want to go outside."
]
```
