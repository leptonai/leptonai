import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";
import { Logo } from "@lepton-dashboard/components/logo";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
export const CenterBox: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();

  return (
    <div
      css={css`
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      `}
    >
      <div
        css={css`
          flex: 0 1 400px;
          padding: 16px 64px;
          * {
            transition: none !important;
          }
          display: flex;
          flex-direction: column;
          text-align: center;
          background: ${theme.colorBgContainer};
          box-shadow: ${theme.boxShadowTertiary};
          border: 1px solid ${theme.colorBorderSecondary};
          border-radius: ${theme.borderRadius}px;
        `}
      >
        <div
          css={css`
            flex: 0 0 auto;
            margin: 32px 0 24px 0;
          `}
        >
          <Logo size="large" />
        </div>
        {children}
      </div>
    </div>
  );
};
