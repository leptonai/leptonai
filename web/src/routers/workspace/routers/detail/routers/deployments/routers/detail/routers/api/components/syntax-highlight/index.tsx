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
          themes: ["nord", "github-light"],
          langs: ["bash", "python"],
        });
      }
      if (inThisTake) {
        const output = highlighter.codeToHtml(code, {
          lang: language,
          theme: currentTheme === "dark" ? "nord" : "github-light",
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
          background-color: rgba(150, 150, 150, 0.1) !important;
        }
      `}
      dangerouslySetInnerHTML={{ __html: highlightedCode }}
      className={`${language}`}
    />
  );
};
