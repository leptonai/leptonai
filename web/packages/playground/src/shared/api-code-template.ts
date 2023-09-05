export const APICodeTemplate = {
  chat: (apiUrl: string, apiKey?: string, prompt?: string) => {
    return {
      Python: `import os
import sys
import openai

openai.api_base = os.environ.get("OPENAI_API_BASE", "${apiUrl}")${
        apiKey ? `\nopenai.api_key = "${apiKey}"` : ""
      }

# List available models
print("==== Available models ====")
models = openai.Model.list()

model = models["data"][0]["id"]

completion = openai.ChatCompletion.create(
    model=model,
    messages=[
        {"role": "user", "content": "${prompt || "say hello"}"},
    ],
    max_tokens=4096,
    stream=True,
)

print(f"==== Model: {model} ====")
for chunk in completion:
    content = chunk["choices"][0]["delta"].get("content")
    if content:
        sys.stdout.write(content)
        sys.stdout.flush()
sys.stdout.write("\\n")`,
      "Node.js": `import OpenAI from 'openai';

const openai = new OpenAI({
  ${apiKey ? `apiKey: '${apiKey}',\n  ` : ""}baseURL: '${apiUrl}'
});

async function main() {
  const completion = await openai.chat.completions.create({
    messages: [{ role: 'user', content: '${prompt || "say hello"}' }],
    model: 'gpt-3.5-turbo',
  });

  console.log(completion.choices);
}

main();`,
      HTTP: `curl ${apiUrl}/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKey || ""}" \\
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "${prompt || "say hello"}"}],
     "temperature": 0.7
   }'`,
    };
  },
  sd: (apiUrl: string, prompt?: string) => {
    // language=Python
    return {
      Python:
        "from leptonai.client import Client\n" +
        `c = Client("${apiUrl}")\n` +
        "\n" +
        "image = c.run(\n" +
        `    prompt="${prompt || "Astronaut on Mars During sunset"}",\n` +
        "    height=1024,\n" +
        "    width=1024,\n" +
        "    seed=1809774958,\n" +
        "    steps=30,\n" +
        "    use_refiner=False\n" +
        ")\n" +
        "with open('output_image.png', 'wb') as f:\n" +
        "    f.write(image)\n" +
        'print("Image saved as output_image.png")',
      HTTP: `curl ${apiUrl} \\
  -H 'Content-Type: application/json' \\
  -d '{
     "width": 1024,
     "height": 1024,
     "seed":151886915,
     "steps":30,
     "use_refiner":false,
     "prompt":"${prompt || "Astronaut on Mars During sunset"}"
   }' \\
  -o output_image.png
   `,
    };
  },
};
