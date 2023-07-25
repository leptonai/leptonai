import { FC, useEffect, useState } from "react";
import {
  getHighlighter,
  Highlighter,
  setCDN,
  renderToHtml,
  IThemedToken,
} from "shiki";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map } from "rxjs";
import { css } from "@emotion/react";
import { Typography } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { CopyFile } from "@carbon/icons-react";

setCDN("/shiki/");

export enum LanguageSupports {
  Bash = "bash",
  Python = "python",
  JSON = "json",
}

const highlighterLoader: Promise<Highlighter> = getHighlighter({
  themes: ["github-dark", "github-light"],
  langs: ["bash", "python", "json"],
});

export const CodeBlock: FC<{
  code: string;
  language: LanguageSupports;
  copyable?: boolean;
  tokenMask?: (content: string, token: IThemedToken) => boolean | string;
}> = ({ code, language, copyable, tokenMask }) => {
  const [highlightedCode, setHighlightedCode] = useState(
    "<pre><code></code></pre>"
  );
  const themeService = useInject(ThemeService);

  const currentTheme = useStateFromObservable(
    () => themeService.theme$.pipe(map(() => themeService.getValidTheme())),
    themeService.getValidTheme()
  );

  useEffect(() => {
    let inThisTake = true;
    const setCode = async () => {
      const highlighter = await highlighterLoader;
      if (inThisTake) {
        const themeName =
          currentTheme === "dark" ? "github-dark" : "github-light";
        const tokens = highlighter.codeToThemedTokens(
          code,
          language,
          themeName,
          {
            includeExplanation: false,
          }
        );
        const _theme = highlighter.getTheme(themeName);
        const codeString = renderToHtml(tokens, {
          fg: _theme.fg,
          bg: _theme.bg,
          themeName,
          elements: {
            token({ style, children, token }) {
              const _mask = tokenMask ? tokenMask(children, token) : false;
              const mask = typeof _mask === "string" || _mask;
              const maskStr =
                typeof _mask === "string"
                  ? _mask
                  : "*".repeat(token.content.length);
              return `<span style="${style}" ${
                mask ? `class="mask-token"` : ""
              }>${
                !mask
                  ? children
                  : `<span class="mask">${maskStr}</span><span class="mask-content">${children}</span>`
              }</span>`;
            },
          },
        });
        setHighlightedCode(codeString);
      }
    };

    setCode().then();

    return () => {
      inThisTake = false;
    };
  }, [language, code, currentTheme, tokenMask]);

  return (
    <div
      css={css`
        position: relative;
        .ant-typography-copy {
          position: absolute;
          top: 12px;
          right: 12px;
          opacity: 0;
          transition: opacity 0.12s ease-in-out;
        }

        &:hover {
          .ant-typography-copy {
            opacity: 1;
          }
        }

        pre {
          min-height: 35px;
          font-size: 12px;
          padding: 12px;
        }
        .mask-token {
          .mask-content {
            display: none;
          }
          &:hover {
            .mask-content {
              display: inline;
            }
            .mask {
              display: none;
            }
          }
        }
      `}
    >
      {copyable && code && (
        <Typography.Text
          copyable={{
            text: code,
            icon: <CarbonIcon icon={<CopyFile />} />,
          }}
        />
      )}
      <div dangerouslySetInnerHTML={{ __html: highlightedCode }} />
    </div>
  );
};
