<img src="https://raw.githubusercontent.com/leptonai/leptonai/main/assets/logo.svg" height=100>

# Lepton AI

**A Pythonic framework to simplify AI service building**

<a href="https://docs.nvidia.com/dgx-cloud/lepton">Homepage</a> •
<a href="https://github.com/leptonai/examples">Examples</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton">Documentation</a> •
<a href="https://docs.nvidia.com/dgx-cloud/lepton/reference/cli">CLI References</a>

The LeptonAI Python library allows you to build an AI service from Python code with ease. Key features include:

- A Pythonic abstraction `Photon`, allowing you to convert research and modeling code into a service with a few lines of code.
- Simple abstractions to launch models like those on [HuggingFace](https://huggingface.co) in few lines of code.
- Prebuilt examples for common models such as Llama, SDXL, Whisper, and others.
- AI tailored batteries included such as autobatching, background jobs, etc.
- A client to automatically call your service like native Python functions.
- Pythonic configuration specs to be readily shipped in a cloud environment.

## Getting started with one-liner
Install the library with:

```shell
pip install -U leptonai
```
This installs the `leptonai` Python library, as well as the commandline interface `lep`. You can then launch a HuggingFace model, say `gpt2`, in one line of code:

```python
lep photon runlocal --name gpt2 --model hf:gpt2
```

If you have access to the Llama2 model ([apply for access here](https://huggingface.co/meta-llama/Llama-2-7b)) and you have a reasonably sized GPU, you can launch it with:

```python
# hint: you can also write `-n` and `-m` for short
lep photon runlocal -n llama2 -m hf:meta-llama/Llama-2-7b-chat-hf
```

(Be sure to use the `-hf` version for Llama2, which is compatible with huggingface pipelines.)

You can then access the service with:

```python
from leptonai.client import Client, local
c = Client(local(port=8080))
# Use the following to print the doc
print(c.run.__doc__)
print(c.run(inputs="I enjoy walking with my cute dog"))
```

Not all HuggingFace models are supported, as many of them contain custom code and are not standard pipelines. If you find a popular model you would like to support, please [open an issue or a PR](https://github.com/leptonai/leptonai/issues/new).

## Checking out more examples

You can find out more examples from the [examples repository](https://github.com/leptonai/examples). For example, launch the Stable Diffusion XL model with:

```shell
git clone git@github.com:leptonai/examples.git
cd examples
```

```python
lep photon runlocal -n sdxl -m advanced/sdxl/sdxl.py
```

Once the service is running, you can access it with:

```python
from leptonai.client import Client, local

c = Client(local(port=8080))

img_content = c.run(prompt="a cat launching rocket", seed=1234)
with open("cat.png", "wb") as fid:
    fid.write(img_content)
```

or access the mounted Gradio UI at [http://localhost:8080/ui](http://localhost:8080/ui). Check the [README file](https://github.com/leptonai/examples/blob/main/advanced/sdxl/README.md) for more details.

## Writing your own photons

Writing your own photon is simple: write a Python Photon class and decorate functions with `@Photon.handler`. As long as your input and output are JSON serializable, you are good to go. For example, the following code launches a simple echo service:

```python
# my_photon.py
from leptonai.photon import Photon

class Echo(Photon):
    @Photon.handler
    def echo(self, inputs: str) -> str:
        """
        A simple example to return the original input.
        """
        return inputs
```

You can then launch the service with:

```shell
lep photon runlocal -n echo -m my_photon.py
```

Then, you can use your service as follows:
```python
from leptonai.client import Client, local

c = Client(local(port=8080))

# will print available paths
print(c.paths())
# will print the doc for c.echo. You can also use `c.echo?` in Jupyter.
print(c.echo.__doc__)
# will actually call echo.
c.echo(inputs="hello world")
```

For more details, checkout the [documentation](https://docs.nvidia.com/dgx-cloud/lepton) and the [examples](https://github.com/leptonai/examples).

## Contributing

Contributions and collaborations are welcome and highly appreciated. Please check out the [contributor guide](https://github.com/leptonai/leptonai/blob/main/CONTRIBUTING.md) for how to get involved.

## License

The Lepton AI Python library is released under the Apache 2.0 license.

Developer Note: early development of LeptonAI was in a separate mono-repo, which is why you may see commits from the `leptonai/lepton` repo. We intend to use this open source repo as the source of truth going forward.
