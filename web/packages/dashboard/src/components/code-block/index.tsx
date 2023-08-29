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

// eslint-disable-next-line react-refresh/only-export-components
export const createDoubleQuoteSecretTokenMasker = (
  secret = "",
  option?: {
    startAt?: number;
    endAt?: number;
  }
) => {
  return (content: string) => {
    if (secret.length === 0) {
      return false;
    }
    const startAt = option?.startAt ?? 0;
    const endAt = option?.endAt ?? secret.length;
    if (content.includes(secret)) {
      const startSubstring = secret.substring(0, startAt);
      const endSubstring = secret.substring(
        secret.length - endAt,
        secret.length
      );
      return `"${startSubstring}${"*".repeat(
        secret.length - startAt - endAt
      )}${endSubstring}"`;
    } else {
      return false;
    }
  };
};

export enum LanguageSupports {
  Bash = "bash",
  Python = "python",
  JSON = "json",
  CSS = "css",
  CPP = "cpp",
  C = "c",
  GO = "go",
  HTML = "html",
  JavaScript = "js",
  TypeScript = "ts",
  Java = "java",
  SQL = "sql",
  YAML = "yaml",
}

const highlighterLoader: Promise<Highlighter> = getHighlighter({
  themes: ["github-dark", "github-light"],
  langs: [
    "bash",
    "python",
    "json",
    "css",
    "cpp",
    "c",
    "go",
    "html",
    "js",
    "ts",
    "java",
    "sql",
    "yaml",
  ],
});

// eslint-disable-next-line react-refresh/only-export-components
export function normalizeLanguage(
  language: string
): LanguageSupports | undefined {
  switch (language) {
    case "shell":
    case "powershell":
    case "bash":
    case "sh":
    case "bat":
      return LanguageSupports.Bash;
    case "python":
    case "py":
      return LanguageSupports.Python;
    case "json":
      return LanguageSupports.JSON;
    case "css":
      return LanguageSupports.CSS;
    case "cpp":
      return LanguageSupports.CPP;
    case "c":
      return LanguageSupports.C;
    case "go":
    case "golang":
      return LanguageSupports.GO;
    case "html":
      return LanguageSupports.HTML;
    case "typescript":
    case "ts":
      return LanguageSupports.TypeScript;
    case "javascript":
    case "js":
      return LanguageSupports.JavaScript;
    case "java":
      return LanguageSupports.Java;
    case "sql":
      return LanguageSupports.SQL;
    case "yaml":
      return LanguageSupports.YAML;
    default:
      return void 0;
  }
}

export const CodeBlock: FC<{
  code: string;
  language?: LanguageSupports;
  copyable?: boolean;
  tokenMask?: (content: string, token: IThemedToken) => boolean | string;
  transparentBg?: boolean;
}> = ({ code, language, copyable, tokenMask, transparentBg }) => {
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
          bg: transparentBg ? "transparent" : _theme.bg,
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
  }, [language, code, currentTheme, tokenMask, transparentBg]);

  return (
    <div
      css={css`
        max-width: 100%;
        max-height: 100%;
        position: relative;
        display: flex;
        overflow: hidden;
        & > div {
          flex: 1;
          display: flex;
          overflow: hidden;
        }

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
          flex: 1;
          overflow: auto;
          min-height: 35px;
          font-size: 12px;
          padding: 12px;
          margin: 0;
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
