import { forwardRef, useRef } from "react";
import {
  Scrollable,
  ScrollableRef,
} from "@lepton-dashboard/components/scrollable";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Code } from "@carbon/icons-react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import { Spin, Typography } from "antd";
import { CodeBlock } from "@lepton/ui/components/code-block";
import { LoadingOutlined } from "@ant-design/icons";
import { normalizeLanguage } from "@lepton/ui/shared/shiki";

let renderCount = 0;

export const MDMessage = forwardRef<
  ScrollableRef,
  {
    content?: string;
    error?: string;
    loading?: boolean;
    responseTime?: number;
    completionTime?: number;
  }
>(({ content, error, loading, completionTime }, ref) => {
  const theme = useAntdTheme();
  const codeRenderCacheRef = useRef<
    Record<string, { priority: number; code: string }>
  >({});

  return (
    <Scrollable
      ref={ref}
      margin="8px"
      position={["start", "end"]}
      css={css`
        flex: 1;
        width: 100%;
        background-color: ${theme.colorBgContainer};
        padding: ${theme.paddingXS}px;
      `}
    >
      {content ? (
        <ReactMarkdown
          remarkPlugins={[remarkBreaks]}
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const language = normalizeLanguage(match?.[1] ?? "py");
              const codePositionId = `${node.position?.start.line}-${node.position?.start.column}-${node.position?.start.offset}`;
              const codeRenderCache =
                codeRenderCacheRef.current[codePositionId]?.code ?? "";
              const priority = renderCount++;
              return !inline ? (
                <CodeBlock
                  {...props}
                  initCode={codeRenderCache}
                  rendered={(code) => {
                    if (
                      !codeRenderCacheRef.current[codePositionId] ||
                      codeRenderCacheRef.current[codePositionId].priority <
                        priority
                    ) {
                      if (completionTime) {
                        delete codeRenderCacheRef.current[codePositionId];
                      } else {
                        codeRenderCacheRef.current[codePositionId] = {
                          priority,
                          code,
                        };
                      }
                    }
                  }}
                  transparentBg
                  copyable={!!completionTime}
                  code={String(children).replace(/\n$/, "")}
                  language={language}
                />
              ) : (
                <Typography.Text code {...props} className={className}>
                  {children}
                </Typography.Text>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      ) : (
        <div
          css={css`
            display: flex;
            flex: 1;
            height: 100%;
            flex-direction: column;
            justify-content: center;
            align-items: center;
          `}
        >
          {error ? (
            <Typography.Text type="danger">{error}</Typography.Text>
          ) : loading ? (
            <>
              <div
                css={css`
                  margin-bottom: 6px;
                `}
              >
                <Spin indicator={<LoadingOutlined />} />
              </div>
              <Typography.Text type="secondary">Generating...</Typography.Text>
            </>
          ) : (
            <span
              css={css`
                font-size: 128px;
                opacity: 0.3;
                color: ${theme.colorBorderSecondary};
              `}
            >
              <CarbonIcon icon={<Code />} />
            </span>
          )}
        </div>
      )}
    </Scrollable>
  );
});
