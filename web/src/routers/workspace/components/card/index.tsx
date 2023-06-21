import { FC, PropsWithChildren, ReactNode } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { Skeleton } from "antd";

export const Card: FC<
  PropsWithChildren<
    {
      icon?: ReactNode;
      title?: ReactNode;
      extra?: ReactNode;
      loading?: boolean;
      borderless?: boolean;
      radiusless?: boolean;
      overflowShow?: boolean;
      shadowless?: boolean;
      paddingless?: boolean;
    } & EmotionProps
  >
> = ({
  children,
  icon,
  title,
  extra,
  loading = false,
  radiusless = false,
  borderless = false,
  overflowShow = false,
  shadowless = false,
  paddingless = false,
  className,
}) => {
  const theme = useAntdTheme();
  return (
    <div
      className={className}
      css={css`
        display: flex;
        flex-direction: column;
        overflow: ${overflowShow ? "visible" : "hidden"};
        background-color: ${theme.colorBgContainer};
        border-color: ${theme.colorBorder};
        border-radius: ${radiusless ? 0 : theme.borderRadius}px;
        border-style: solid;
        border-width: ${borderless ? 0 : "1px"};
        box-shadow: ${shadowless ? "none" : theme.boxShadowTertiary};
      `}
    >
      {title && (
        <div
          css={css`
            flex: 0 0 48px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid ${theme.colorBorder};
            background-color: ${theme.colorBgContainer};
            color: ${theme.colorTextHeading};
            font-size: 14px;
            font-weight: 500;
            padding: 0 16px;
          `}
        >
          <div
            css={css`
              width: 100%;
              display: ${icon ? "flex" : "block"};
            `}
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
            {title}
          </div>
          {extra && (
            <div
              css={css`
                flex: 0 0 auto;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 8px;
              `}
            >
              {extra}
            </div>
          )}
        </div>
      )}
      <div
        css={css`
          flex: 1 1 auto;
          position: relative;
          padding: ${paddingless ? 0 : "16px"};
        `}
      >
        {loading ? <Skeleton /> : children}
      </div>
    </div>
  );
};
