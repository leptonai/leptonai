import { FC } from "react";
import { LeptonIcon } from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const Logo: FC<
  { size?: "default" | "large"; enableLogoHref?: boolean } & EmotionProps
> = ({ size = "default", className, enableLogoHref = false }) => {
  const theme = useAntdTheme();
  return (
    <a
      href="https://lepton.ai"
      target="_blank"
      className={className}
      css={css`
        pointer-events: ${enableLogoHref ? "auto" : "none"};
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${size === "default" ? "26px" : "38px"};
      `}
      rel="noreferrer"
    >
      <LeptonIcon />
      <div
        css={css`
          font-size: ${size === "default" ? "18px" : "26px;"};
          margin-left: 12px;
          font-weight: 600;
          color: ${theme.colorTextHeading};
        `}
      >
        Lepton AI
      </div>
    </a>
  );
};
