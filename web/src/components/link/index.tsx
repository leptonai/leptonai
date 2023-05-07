import { Link as RouterLink, RelativeRoutingType, To } from "react-router-dom";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, PropsWithChildren, ReactNode } from "react";
import { css } from "@emotion/react";

export const Link: FC<
  PropsWithChildren<{
    to: To;
    relative?: RelativeRoutingType;
    icon?: ReactNode;
  }>
> = ({ children, to, relative = "path", icon }) => {
  const theme = useAntdTheme();
  return (
    <RouterLink
      css={css`
        color: inherit;
        display: inline-flex;
        &:hover {
          color: ${theme.colorTextHeading};
          text-decoration: underline;
        }
      `}
      to={to}
      relative={relative}
    >
      {icon && (
        <div
          css={css`
            margin-right: 8px;
          `}
        >
          {icon}
        </div>
      )}
      {children}
    </RouterLink>
  );
};
