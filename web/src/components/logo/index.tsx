import { FC } from "react";
import { LeptonIcon } from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const Logo: FC<{ size?: "default" | "large" } & EmotionProps> = ({
  size = "default",
  className,
}) => {
  const theme = useAntdTheme();
  return (
    <div
      className={className}
      css={css`
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${size === "default" ? "26px" : "38px"};
      `}
    >
      <LeptonIcon />
      <div
        css={css`
          font-size: ${size === "default" ? "20px" : "26px;"};
          margin-left: 16px;
          cursor: default;
          font-weight: 600;
          color: ${theme.colorTextHeading};
        `}
      >
        Lepton AI
      </div>
    </div>
  );
};
