import { FC, useEffect, useState } from "react";
import type { IThemedToken } from "shiki";
import { css } from "@emotion/react";
import { Languages, useBrowserShiki } from "@lepton/ui/shared/shiki";
import { CopyButton } from "@lepton/ui/components/copy-button";

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

export const CodeBlock: FC<{
  code: string;
  initCode?: string;
  language?: Languages;
  rendered?: (code: string) => void;
  copyable?: boolean;
  tokenMask?: (content: string, token: IThemedToken) => boolean | string;
  transparentBg?: boolean;
  theme?: string;
}> = ({
  code,
  rendered,
  initCode = "<pre><code></code></pre>",
  language,
  copyable,
  tokenMask,
  transparentBg,
}) => {
  const [highlightedCode, setHighlightedCode] = useState(initCode);
  const { getHighlighter, renderToHtml, themeMode } = useBrowserShiki();

  useEffect(() => {
    let inThisTake = true;
    const setCode = async () => {
      const highlighter = await getHighlighter();
      if (inThisTake) {
        const themeName = themeMode === "dark" ? "github-dark" : "github-light";
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
        rendered?.(codeString);
      }
    };

    setCode().then();

    return () => {
      inThisTake = false;
    };
  }, [language, code, themeMode, tokenMask, transparentBg, rendered]);

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

        .copy-button {
          position: absolute;
          top: 12px;
          right: 12px;
          opacity: 0;
          transition: opacity 0.12s ease-in-out;
        }

        &:hover {
          .copy-button {
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
      {copyable && code && <CopyButton className="copy-button" value={code} />}
      <div dangerouslySetInnerHTML={{ __html: highlightedCode }} />
    </div>
  );
};
