import { FC, useEffect, useState } from "react";
import { getHighlighter, Highlighter, setCDN } from "shiki";
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

let highlighter: Highlighter;

export const CodeBlock: FC<{
  code: string;
  language: LanguageSupports;
  copyable?: boolean;
}> = ({ code, language, copyable }) => {
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
        position: relative;
        .ant-typography-copy {
          position: absolute;
          top: 8px;
          right: 8px;
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
