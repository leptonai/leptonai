import { FC, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import { CodeBlock } from "@lepton/ui/components/code-block";
import { normalizeLanguage } from "@lepton/ui/shared/shiki";
import { Icons } from "@lepton/ui/components/icons";
import { Typography } from "@lepton/ui/components/typography";
import { Code } from "@carbon/icons-react";

let renderCount = 0;

export const MDMessage: FC<{
  content?: string;
  error?: string;
  loading?: boolean;
  responseTime?: number;
  completionTime?: number;
  single?: boolean;
}> = ({ content, error, loading, completionTime, single }) => {
  const codeRenderCacheRef = useRef<
    Record<string, { priority: number; code: string }>
  >({});

  const markdownNode = useMemo(() => {
    /* eslint-disable react/no-children-prop */
    return (
      <ReactMarkdown
        children={content ?? ""}
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
              <Typography.Code {...props} className={className}>
                {children}
              </Typography.Code>
            );
          },
        }}
      />
    );
  }, [completionTime, content]);

  return (
    <>
      {content ? (
        <>{markdownNode}</>
      ) : (
        <div className="flex flex-col justify-center items-center h-full">
          {error ? (
            <span className="text-sm text-destructive">{error}</span>
          ) : loading ? (
            <>
              <div className="mb-1">
                {single && (
                  <Icons.Spinner className="mr-2 h-4 w-4 animate-spin" />
                )}
              </div>
              <span className="text-sm text-muted-foreground">
                Generating...
              </span>
            </>
          ) : single ? (
            <Code className="w-40 h-40 opacity-30 text-muted-foreground/[.3]" />
          ) : (
            <span className="text-sm text-muted-foreground">(empty)</span>
          )}
        </div>
      )}
    </>
  );
};
