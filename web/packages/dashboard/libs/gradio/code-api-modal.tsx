import { Button, message, Modal, Space } from "antd";
import { FC, PropsWithChildren, ReactNode, useCallback } from "react";
import {
  CodeBlock,
  createDoubleQuoteSecretTokenMasker,
} from "@lepton/ui/components/code-block";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

// eslint-disable-next-line react-refresh/only-export-components
export const APICodeTemplates = {
  chat: (apiUrl: string, apiKey?: string, prompt?: string) => {
    // language=Python
    return `import os
import sys
import openai

openai.api_base = os.environ.get("OPENAI_API_BASE", "${apiUrl}")${
      apiKey ? `\nopenai.api_key = ${apiKey}` : ""
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
sys.stdout.write("\\n")`;
  },
  sd: (apiUrl: string, prompt?: string) => {
    // language=Python
    return (
      "import requests\n" +
      "\n" +
      `url = "${apiUrl}"\n` +
      "\n" +
      "payload = {\n" +
      '    "height": 1024,\n' +
      `    "prompt": "${prompt || "Astronaut on Mars During sunset"}",\n` +
      '    "seed": 1809774958,\n' +
      '    "steps": 30,\n' +
      '    "use_refiner": False,\n' +
      '    "width": 1024,\n' +
      "}\n" +
      "\n" +
      "headers = {\n" +
      '    "Content-Type": "application/json"\n' +
      "}\n" +
      "\n" +
      "response = requests.post(url, json=payload, headers=headers)\n" +
      "\n" +
      "if response.status_code == 200:\n" +
      "    # Assuming the response contains the image data\n" +
      "    with open('output_image.png', 'wb') as f:\n" +
      "        f.write(response.content)\n" +
      '    print("Image saved as output_image.png")\n' +
      "else:\n" +
      '    print(f"Error {response.status_code}: {response.text}")\n'
    );
  },
};

export const CodeAPIModal: FC<
  {
    code: string;
    maskString?: string;
    title?: ReactNode;
    open: boolean;
    setOpen: (v: boolean) => void;
  } & PropsWithChildren
> = ({ title, code, open, setOpen, maskString }) => {
  const theme = useAntdTheme();
  const copy = useCallback(() => {
    void navigator.clipboard.writeText(code);
    void message.success("Copied");
  }, [code]);
  return (
    <Modal
      width={600}
      onCancel={() => setOpen(false)}
      open={open}
      title={title}
      footer={
        <Space
          css={css`
            width: 100%;
            flex-direction: row-reverse;
          `}
        >
          <Button type="primary" onClick={copy}>
            Copy to Clipboard
          </Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </Space>
      }
    >
      <div
        css={css`
          height: 400px;
          border: 1px solid ${theme.colorBorder};
          background: ${theme.colorBgLayout};
          overflow: hidden;
          border-radius: ${theme.borderRadius}px;
        `}
      >
        <CodeBlock
          transparentBg
          tokenMask={createDoubleQuoteSecretTokenMasker(maskString || "", {
            startAt: 3,
            endAt: 3,
          })}
          code={code}
          language="python"
        />
      </div>
    </Modal>
  );
};
