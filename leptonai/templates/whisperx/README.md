# WhisperX

WhisperX is a fast automatic speech recognition (ASR) implementation based on the OpenAI Whisper model. It also has word-level timestamps and speaker diarization capabilities. For more details, check out the [github page](https://github.com/m-bain/whisperX).

# Example Usage

```python
from leptonai.client import Client

c = Client(WORKSPACE_NAME, DEPLOYMENT_NAME, token=YOUR_TOKEN)
result = c.run(
    input="https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac",
    language="en", # optional, default is "en"
    min_speakers=1, # optional, only applicable if trancribe_only is False
    max_speakers=2, # optional, only applicable if trancribe_only is False
    trancribe_only=True, # optional, default is True
)
```

The input can be a URL pointing to an audio file. If you are using a local file, you can send it to the deployment using the `File` class:
```python
from leptonai.photon import File

with open("local_file.wav", "rb") as f:
    result = c.run(input=File(f))
```

## Output

If `trancribe_only` is `True`, the result will be a list of maps, each containing a chunk of text and its start and end timestamps, such as:
```
[{
    'text': ' he hoped there would be stew for dinner turnips and carrots and bruised potatoes and fat mutton pieces to be ladled out in thick peppered flour fattened sauce',
    'start': 0.009,
    'end': 10.435
}]
```

If `trancribe_only` is `False`, the result will also contain a word-level start and end of words, as well as the speaker of that word, such as:
```
[{
    'start': 0.569,
    'end': 10.015,
    'text': ' he hoped there would be stew for dinner turnips and carrots and bruised potatoes and fat mutton pieces to be ladled out in thick peppered flour fattened sauce',
    'words': [
        {'word': 'he', 'start': 0.569, 'end': 0.649, 'score': 0.958, 'speaker': 'SPEAKER_00'},
        {'word': 'hoped', 'start': 0.709, 'end': 0.97, 'score': 0.72, 'speaker': 'SPEAKER_00'},
        ... (many omitted here) ...
    ],
    'speaker': 'SPEAKER_00'
}]
```

# Configurations

This deployment will require a GPU. As a result, make sure you use a GPU resource shape.

To customize the deployment, you can set the following environmental variables.

* `MAX_LENGTH_IN_SECONDS`: the maximum length of the audio in seconds. This prevents the model from dealing with overly long audio inputs and blocking other inference requests.
* `WHISPER_MODEL`: the model to run, such as "large-v2" or "large-v3".

This deployment also requires the following secrets to run:

* `HUGGING_FACE_HUB_TOKEN`: the token to access the Hugging Face model hub. You can create one or find your existing token at [the hf settings page](https://huggingface.co/settings/tokens).
