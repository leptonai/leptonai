import { FC, useEffect, useState } from "react";
import { getHighlighter, Highlighter, setCDN } from "shiki";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map } from "rxjs";
import { css } from "@emotion/react";

setCDN("/shiki/");

export enum LanguageSupports {
  Bash = "bash",
  Python = "python",
  JSON = "json",
}

let highlighter: Highlighter;

export const SyntaxHighlight: FC<{
  code: string;
  language: LanguageSupports;
}> = ({ code, language }) => {
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
      if (!highlighter) {
        highlighter = await getHighlighter({
          themes: ["github-dark", "github-light"],
          langs: ["bash", "python", "json"],
        });
      }
      if (inThisTake) {
        const output = highlighter.codeToHtml(code, {
          lang: language,
          theme: currentTheme === "dark" ? "github-dark" : "github-light",
        });
        setHighlightedCode(output);
      }
    };

    setCode().then();

    return () => {
      inThisTake = false;
    };
  }, [language, code, currentTheme]);

  return (
    <div
      css={css`
        pre {
          min-height: 35px;
          font-size: 12px;
          padding: 12px;
        }
      `}
      dangerouslySetInnerHTML={{ __html: highlightedCode }}
      className={`${language}`}
    />
  );
};
