import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const Hoverable: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        color: inherit;
        &:hover {
          color: ${theme.colorTextHeading};
        }
      `}
    >
      {children}
    </div>
  );
};
