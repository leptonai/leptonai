import { Link as RouterLink, RelativeRoutingType, To } from "react-router-dom";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";

export const Link: FC<
  PropsWithChildren<{ to: To; relative?: RelativeRoutingType }>
> = ({ children, to, relative = "path" }) => {
  const theme = useAntdTheme();
  return (
    <RouterLink
      css={css`
        color: inherit;
        &:hover {
          color: ${theme.colorTextHeading};
        }
      `}
      to={to}
      relative={relative}
    >
      {children}
    </RouterLink>
  );
};
