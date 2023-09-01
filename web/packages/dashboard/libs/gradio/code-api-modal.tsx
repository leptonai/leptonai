import { Languages } from "@lepton/ui/shared/shiki";
import { Button, message, Modal, Space, Tabs } from "antd";
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
} from "@lepton/ui/components/code-block";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export const CodeAPIModal: FC<
  {
    codes: { language: string; code: string }[];
    maskString?: string;
    title?: ReactNode;
    open: boolean;
    setOpen: (v: boolean) => void;
  } & PropsWithChildren
> = ({ title, codes, open, setOpen, maskString }) => {
  const theme = useAntdTheme();
  const [language, setLanguage] = useState(codes[0].language);
  const activeCode = useMemo(
    () => codes.find((c) => c.language === language)!.code,
    [language, codes]
  );
  const highlightLanguage: Languages = useMemo(() => {
    const languageMap: { [key: string]: Languages } = {
      Python: "python",
      HTTP: "bash",
      "Node.js": "js",
    };
    return languageMap[language] || "bash";
  }, [language]);
  const copy = useCallback(() => {
    void navigator.clipboard.writeText(activeCode);
    void message.success("Copied");
  }, [activeCode]);
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
      <Tabs
        css={css`
          .ant-tabs-nav-wrap {
            justify-content: right !important;
          }
        `}
        size="small"
        activeKey={language}
        onChange={setLanguage}
        items={codes.map((c) => ({
          key: c.language,
          label: c.language,
          children: (
            <div
              css={css`
                height: 300px;
                border: 1px solid ${theme.colorBorderSecondary};
                background: ${theme.colorBgLayout};
                overflow: hidden;
                border-radius: 0 0 ${theme.borderRadius}px
                  ${theme.borderRadius}px;
                border-top: none;
                position: relative;
                top: -16px;
              `}
            >
              <CodeBlock
                transparentBg
                copyable
                tokenMask={createDoubleQuoteSecretTokenMasker(
                  maskString || "",
                  {
                    startAt: 3,
                    endAt: 3,
                  }
                )}
                code={activeCode}
                language={highlightLanguage}
              />
            </div>
          ),
        }))}
      />
    </Modal>
  );
};
