import sys

import openai

openai.api_base = "http://0.0.0.0:8080/v1"
openai.api_key = "api-key"

# List available models
print("==== Available models ====")
print(openai.Model.list())

sys_prompt = """
The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
"""

# vicuna-7b
completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "tell me a long story"},
    ],
    stream=True,
)
print("==== Model gpt-3.5-turbo ====")
for chunk in completion:
    content = chunk["choices"][0]["delta"].get("content")
    if content:
        sys.stdout.write(content)
        sys.stdout.flush()
sys.stdout.write("\n")
