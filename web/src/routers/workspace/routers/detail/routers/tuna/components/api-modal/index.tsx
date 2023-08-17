import { Button, message, Modal, Space, Tooltip } from "antd";
import { SizeType } from "antd/lib/config-provider/SizeContext";
import {
  FC,
  PropsWithChildren,
  ReactNode,
  useCallback,
  useMemo,
  useState,
} from "react";
import {
  CodeBlock,
  createDoubleQuoteSecretTokenMasker,
  LanguageSupports,
} from "@lepton-dashboard/routers/workspace/components/code-block";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export interface ApiModalProps {
  name: string;
  size?: SizeType;
  apiUrl: string;
  apiKey?: string;
  disabled?: boolean;
  icon?: ReactNode;
}
export const ApiModal: FC<ApiModalProps & PropsWithChildren> = ({
  name,
  apiUrl,
  apiKey,
  size,
  disabled,
  icon,
  children,
}) => {
  const theme = useAntdTheme();
  const [open, setOpen] = useState(false);

  const pythonCode = useMemo(() => {
    return `import os
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
        {"role": "user", "content": "say hello"},
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
  }, [apiUrl, apiKey]);

  const copy = useCallback(() => {
    void navigator.clipboard.writeText(pythonCode);
    void message.success("Copied");
  }, [pythonCode]);
  return (
    <>
      <Tooltip placement="top" title="Get code template for this tuna">
        <Button
          disabled={disabled}
          size={size}
          key="deploy"
          type="text"
          icon={icon}
          onClick={() => setOpen(true)}
        >
          {children}
        </Button>
      </Tooltip>

      <Modal
        width={600}
        onCancel={() => setOpen(false)}
        open={open}
        title={`Copy API for ${name}`}
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
            tokenMask={createDoubleQuoteSecretTokenMasker(apiKey || "", {
              startAt: 3,
              endAt: 3,
            })}
            code={pythonCode}
            language={LanguageSupports.Python}
          />
        </div>
      </Modal>
    </>
  );
};
