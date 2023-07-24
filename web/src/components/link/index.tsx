import { Link as RouterLink, RelativeRoutingType, To } from "react-router-dom";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { forwardRef, PropsWithChildren, ReactNode } from "react";
import { css } from "@emotion/react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const Link = forwardRef<
  HTMLAnchorElement,
  PropsWithChildren<{
    underline?: boolean;
    to: To;
    target?: string;
    relative?: RelativeRoutingType;
    icon?: ReactNode;
  }> &
    EmotionProps
>(
  (
    {
      children,
      target,
      to,
      relative = "path",
      icon,
      className,
      underline = true,
    },
    ref
  ) => {
    const theme = useAntdTheme();
    return (
      <RouterLink
        className={className}
        css={css`
          color: inherit;
          display: inline-flex;
          align-items: center;
          &:hover {
            color: ${theme.colorTextHeading};
            text-decoration: ${underline ? "underline" : "none"};
          }
        `}
        ref={ref}
        to={to}
        target={target}
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
  }
);