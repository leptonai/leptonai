import { FC, useMemo } from "react";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const Result: FC<{ result: unknown }> = ({ result }) => {
  const displayResult = useMemo(() => {
    if (typeof result === "string" || typeof result === "number") {
      return result;
    } else if (typeof result === "object") {
      return JSON.stringify(result);
    } else {
      return "outputs format not supported";
    }
  }, [result]);
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        margin: 0;
        background: ${theme.colorBgLayout};
        height: 100%;
        border: 1px solid ${theme.colorBorder};
        border-radius: ${theme.borderRadius}px;
        word-break: break-word;
        white-space: pre-wrap;
        color: ${theme.colorText};
        padding: 32px;
      `}
    >
      {displayResult}
    </div>
  );
};
