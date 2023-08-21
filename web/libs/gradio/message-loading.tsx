import { css, keyframes } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC } from "react";

const loadingOne = keyframes`
  0% {
    transform: scale(0.5);
  }
  100% {
    transform: scale(1);
  }
`;
const loadingTwo = keyframes`
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(16px, 0);
  }
`;
const loadingThree = keyframes`
  0% {
    transform: scale(1);
  }
  100% {
    transform: scale(0.5);
  }
`;

export const MessageLoading: FC = () => {
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        display: inline-block;
        position: relative;
        width: 80px;
        height: 24px;
        div {
          position: absolute;
          top: 9px;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: ${theme.colorTextSecondary};
          animation-timing-function: cubic-bezier(0, 1, 1, 0);
        }
      `}
    >
      <div
        css={css`
          left: 0;
          animation: ${loadingOne} 0.6s infinite;
        `}
      />
      <div
        css={css`
          left: 8px;
          animation: ${loadingTwo} 0.6s infinite;
        `}
      />
      <div
        css={css`
          left: 24px;
          animation: ${loadingTwo} 0.6s infinite;
        `}
      />
      <div
        css={css`
          left: 48px;
          animation: ${loadingThree} 0.6s infinite;
        `}
      />
    </div>
  );
};
