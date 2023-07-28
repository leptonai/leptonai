import { FC, PropsWithChildren, ReactNode } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export const ChatContainer: FC<PropsWithChildren & { header: ReactNode }> = ({
  header,
  children,
}) => {
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        display: flex;
        flex-direction: column;
        height: 100%;
        width: 100%;
      `}
    >
      <div
        css={css`
          flex: 0;
          border-bottom: 1px solid ${theme.colorBorder};
        `}
      >
        {header}
      </div>
      <div
        css={css`
          flex: 1;
          overflow: hidden;
        `}
      >
        {children}
      </div>
    </div>
  );
};
