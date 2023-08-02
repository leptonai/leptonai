import { Link as RouterLink, RelativeRoutingType, To } from "react-router-dom";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { forwardRef, PropsWithChildren, ReactNode } from "react";
import { css } from "@emotion/react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const Link = forwardRef<
  HTMLAnchorElement,
  PropsWithChildren<{
    underline?: boolean;
    to?: To;
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
    const inner = (
      <>
        {" "}
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
      </>
    );
    const cssClassName = css`
      color: inherit;
      display: inline-flex;
      align-items: center;
      cursor: pointer;
      &:hover {
        color: ${theme.colorTextHeading};
        text-decoration: ${underline ? "underline" : "none"};
      }
    `;

    if (to) {
      return (
        <RouterLink
          className={className}
          css={cssClassName}
          ref={ref}
          to={to}
          target={target}
          relative={relative}
        >
          {inner}
        </RouterLink>
      );
    } else {
      return (
        <span className={className} css={cssClassName} ref={ref}>
          {inner}
        </span>
      );
    }
  }
);
