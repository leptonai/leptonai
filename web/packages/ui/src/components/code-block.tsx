import { FC, useEffect, useState } from "react";
import type { IThemedToken } from "shiki";
import { Languages, useBrowserShiki } from "@lepton/ui/shared/shiki";
import { CopyButton } from "@lepton/ui/components/copy-button";

export const createStringLiteralSecretTokenMasker = (
  secret = "",
  option?: {
    startAt?: number;
    endAt?: number;
    template?: (quote: string, secret: string) => string;
  }
) => {
  return (content: string) => {
    if (secret.length === 0) {
      return false;
    }
    const startAt = option?.startAt ?? 0;
    const endAt = option?.endAt ?? secret.length;
    if (
      content.includes(secret) &&
      (content.startsWith("&#39;") || content.startsWith("&quot;"))
    ) {
      const quote = content.startsWith("&quot;") ? '"' : "'";
      const startSubstring = secret.substring(0, startAt);
      const endSubstring = secret.substring(
        secret.length - endAt,
        secret.length
      );
      const markedSecret = `${startSubstring}${"*".repeat(
        secret.length - startAt - endAt
      )}${endSubstring}`;
      const template =
        option?.template ?? ((quote, secret) => `${quote}${secret}${quote}`);
      return template(quote, markedSecret);
    } else {
      return false;
    }
  };
};

const preClassname = "flex-1 overflow-auto min-h-[35px] text-xs p-2 m-0";

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
  initCode = `<pre class="${preClassname}"><code></code></pre>`,
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
              return `<span style="${style}" class="group/mask">${
                !mask
                  ? children
                  : `<span class="group-hover/mask:hidden">${maskStr}</span><span class="hidden group-hover/mask:inline">${children}</span>`
              }</span>`;
            },
            pre({ children }) {
              return `<pre class="${preClassname}">${children}</pre>`;
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
  }, [
    language,
    code,
    themeMode,
    tokenMask,
    transparentBg,
    rendered,
    getHighlighter,
    renderToHtml,
  ]);

  return (
    <div className="group/code-block flex w-full h-full relative overflow-hidden">
      {copyable && code && (
        <CopyButton
          className="absolute top-2 right-2 opacity-0 transition-opacity hover:bg-secondary bg-secondary/80 group-hover/code-block:opacity-100"
          value={code}
        />
      )}
      <div
        className="flex-1 flex overflow-hidden"
        dangerouslySetInnerHTML={{ __html: highlightedCode }}
      />
    </div>
  );
};
