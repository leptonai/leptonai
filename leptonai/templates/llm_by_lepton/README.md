# Lepton LLM

The LLM Engine by Lepton provides fast and easy deployment of popular open source LLM models, at users' full control. We have built it with compatibility for major LLM architectures, with common optimization technique like dynamic batching, quantization, speculatively execution, and more. We also provide an OpenAI-compatible API to deploy your own fine-tuned LLM models, so you can use it as a drop-in replacement for the OpenAI API.

# Configurations

You only need to set the following environmental variables to launch an open source LLM model. To run your own fine-tuned model or multiple LORA in the same deployment, you are more than welcome to contact us at [info@lepton.ai](mailto:info@lepton.ai).

Set the following environmental variables.

* `MODEL_PATH`: The model to run. This can be a HuggingFace model string, such as "meta-llama/Llama-2-13b-chat-hf", or "mistralai/Mistral-7B-v0.1". It could also be a path to a custom model mounted via the Lepton storage (enterprise feature - feel free to [talk to us](mailto:info@lepton.ai)).
* `USE_INT`: (Optional) Set to true to apply quantization techniques for reducing GPU memory usage. For model size under 7B, or 13B with USE_INT set to true, gpu.a10 is sufficient to run the model, although you might want to use more powerful computation resources.
* `TUNA_STREAM_CB_STEP`: (Optional) in streaming mode, the minimum number of tokens to generate in each new chunk. Smaller numbers send generated results sooner, but may lead to a slightly higher network overhead. Default value set to 3. Unless you are hyper-tuning for benchmarks, you can leave this value as default.
* `MEDUSA`: (Optional) Run the inference with a pre-trained [Medusa](https://arxiv.org/abs/2401.10774) speculative decoding model. For example, to speed up llama2-70b, use `leptonai/Llama-2-70b-chat-4-heads`. We have provided a set of pre-trained medusa heads on [HuggingFace](https://huggingface.co/leptonai). To train medusa heads on your own model or with your own data, please [talk to us](mailto:info@lepton.ai).
* `LORAS`: (Optional) We support running LORA models (also known as PEFT models) in the same deployment as the main model, by setting LORAS in a format `model_id:model_name`. If you have multiple models, separate them by `|`. For example, [therealcyberlord/llama2-qlora-finetuned-medical](https://huggingface.co/therealcyberlord/llama2-qlora-finetuned-medical) is based on `meta-llama/Llama-2-7b-chat-hf`, and you can specify `therealcyberlord/llama2-qlora-finetuned-medical:medical` to run it. On the client side, invoke it with `model=medical`.
* `LEPTON_CHAT_TEMPLATE`: (Optional) We support selecting a chat template automatically based on the model name. If you want to set a specific chat template, you can set this variable based on the following chat template names:
    <details>
        <summary>Supported chat templates</summary>
        <table>
            <thead>
                <tr>
                    <th>Base Model Name</th>
                    <th>Chat Template Name</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Baichuan</td>
                    <td>baichuan (for baichuan 1/2)</td>
                </tr>
                <tr>
                    <td>ChatGLM</td>
                    <td>chatglm2, chatglm-chatml (for chatglm3, glm-4-chat)</td>
                </tr>
                <tr>
                    <td>DBRX</td>
                    <td>dbrx</td>
                </tr>
                <tr>
                    <td>Falcon</td>
                    <td>falcon</td>
                </tr>
                <tr>
                    <td>Gemma</td>
                    <td>gemma (for gemma1/2)</td>
                </tr>
                <tr>
                    <td>LLaMA</td>
                    <td>llama-2, llama-3, codellama</td>
                </tr>
                <tr>
                    <td>LLaVA / LLavA-Next</td>
                    <td>llama-2</td>
                </tr>
                <tr>
                    <td>Mistral / Mixtral</td>
                    <td>mistral</td>
                </tr>
                <tr>
                    <td>Qwen</td>
                    <td>qwen (for qwen1/1.5/2)</td>
                </tr>
                <tr>
                    <td>Vicuna</td>
                    <td>vicuna</td>
                </tr>
                <tr>
                    <td>Zephyr</td>
                    <td>zephyr</td>
                </tr>
                <tr>
                    <td>Others</td>
                    <td>openchat</td>
                </tr>
            </tbody>
        </table>
    </details>

* `LEPTON_CHAT_TEMPLATE_JINJA`: (Optional) If you want to use a custom jinja chat template, you can set LEPTON_CHAT_TEMPLATE_JINJA as a string of jinja, then the lepton llm will format the chat messages following the custom template with the highest priority.

This deployment may also require the following secret(s) to run:

* `HUGGING_FACE_HUB_TOKEN`: (Optional) the token to access the Hugging Face model hub. You can create one or find your existing token at [the hf settings page](https://huggingface.co/settings/tokens).

Once these fields are set, click `Deploy` button at the bottom of the page to create the deployment. You can see the deployment has now been created under [Deployments](https://dashboard.lepton.ai/workspace-redirect/deployments).

# Using the model with OpenAI SDK
Our deployment is fully compatible with the OpenAI SDK. If you have not installed it, do it via:

```bash
pip install -U openai
```

Note that, openai has breaking changes introduced in its version 1.x. The code below works for version after 1.0, and if you are using e.g. 0.28.x, some syntax might need changing. Our deployment works with both pre- and post-1.0 versions.

Set `YOUR_DEPLOYMENT_URL` and `YOUR_API_TOKEN` to the deployment name and the API token of your workspace. The deployment URL can be found on top of the deployment detail page, and the API token could be found at the API tab or under [Settings.](https://dashboard.lepton.ai/workspace-redirect/settings/api-tokens)

For your convenience, you can keep using the model string like “gpt-3.5-turbo” as the model argument - our LLM engine automatically fills in these model names as a placeholder, so you don't have to change any custom code. Do remember that, it’s just an alias for the actual model you invoke in this case, and not the OpenAI model.

## Completion

```python
import openai

client = openai.OpenAI(
    base_url= "YOUR_DEPLOYMENT_URL" + "/api/v1/", 
    api_key= "YOUR_API_TOKE",
)

completion = client.completions.creat(
    # All requests will be routed to your model within this deployment.
	model="gpt-3.5-turbo", 
    prompt="This is a test"
)

print(completion.choices[0].text)
```

## Chat Completion

```python
import openai

client = openai.OpenAI(
    base_url= "YOUR_DEPLOYMENT_URL" + "/api/v1/", 
    api_key= "YOUR_API_TOKE",
)

completion = client.chat.completions.create(
    # All requests will be routed to your model within this deployment.
	model="gpt-3.5-turbo", 
    messages=[
      {"role": "user", "content": "When was the Apollo 11 launched"}
    ]
)

print(completion.choices[0].message)
```

Moreover, if you want to use `completion` instead of `chat completion` to achieve similar results, you can format your chat messages to prompt locally, here is an example:

```python
import openai
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained('YOUR_TOKENIZER_PATH')
messages = [
    {"role": "user", "content": "When was the Apollo 11 launched"}
]
# If your tokenizer does not have a built-in chat template,
# you can load a jinja template and set it as tokenizer.chat_template
prompt = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)

client = openai.OpenAI(
    base_url= "YOUR_DEPLOYMENT_URL" + "/api/v1/", 
    api_key= "YOUR_API_TOKE",
)

completion = client.completions.creat(
    # All requests will be routed to your model within this deployment.
	model="gpt-3.5-turbo", 
    prompt=prompt
)

print(completion.choices[0].text)
```

# FAQs

Q: What models are supported? If the model I am interested in is not supported, what will happen? 

A: The currently supported model architectures are: Llama, Codellama, Falcon, mistral, mixtral, qwen, baichuan, Yi, starcoder. If you find a model you'd like to use that is not supported, you can create an issue on our [GitHub page](https://github.com/leptonai/leptonai), or contact us at [info@lepton.ai](mailto:info@lepton.ai).

Q: Can I run models bigger than 7B or 13b (such as llama 70B), which would need more than A10 machines? 

A: Yes, we do support these models if you chooose a larger resource shape, like A100 or H100. Kindly understand that such resources are not always available on-demand. We support reserved capacities for such resources - sending a mail to info@lepton.ai. if intersted.

Q: How do I start an LLM engine runtime via CLI?

A: Here is the example. Replace `my-llm` with the name of your choice:

```bash
lep photon run -n llm-by-lepton \
    --deployment-name my-llm  \
	--resource-shape gpu.a10 \
	--env MODEL_PATH=mistralai/Mistral-7B-v0.1 \
	--public-photon 
```
Note that `--public-photon` is required to obtain the runtime image from the public photon templates.

For more reference on using CLI, you may checkout the [CLI Reference](https://www.lepton.ai/references/lep_photon#lep-photon-run).

Q: Where can I find and setup my huggingface token as a secret:

A: You can find your huggingface token [here](https://huggingface.co/settings/tokens). After retrieving the token, you may setup the token as a secret in the [Secrets](https://dashboard.lepton.ai/workspace-redirect/settings/secrets) page.

Q: The deployment seems to be stuck for a while or failed, how to deal with it?

A: Click on the deployment name to navigate to the deployment detail page. Under `Replica` tabs, you’ll see the detailed message and status of your replica. If you are confused with the message, you could create an issue on our [GitHub page](https://github.com/leptonai/leptonai).

Q: The python client runs into an issue like `AttributeError` , how to deal with it?

A: Make sure your `openai` version is updated and rerun the code above. If this doesn’t work, you could create an issue on our [GitHub page](https://github.com/leptonai/leptonai).

Q: Why is `gpt-3.5-turbo` used in the sample request code?

A:  Each Lepton LLM deployment hosts the model you specify, but in many cases (especially when you are using third-party libraries), some of the client code may have hard-coded `gpt-3.5-turbo` in their code. As a result, for the convenience of users, we provide the name as a placeholder, and under the hood route to the model being served.

Q: Can I use other languages such as NodeJS or HTTP to access my deployment?

A: Yes, you could! You could use Open AI NodeJS Library or HTTP requests to access your deployment as well. Simply replace `[api.openai.com](http://api.openai.com)` and `OPENAI_API_KEY` with your deployment URL and the API token will work.

Q: Will `USE_INT` setup affect the result?

A: The `USE_INT` environment variable will apply quantization to your choice of model. And this could affect the result. Our experience suggests that INT8 does not significantly alter the result quality. For a more detailed evaluation on what is the best set up for your use case, please reach out to us and we can design optimization POC strategies together.

Q: Can I run this deployment on my local machine or dev VM?

A: For enterprise users, we provide on-prem deployment and support for the same LLM engine that runs on our platform. Please contact us via info@lepton.ai if you are interested.
