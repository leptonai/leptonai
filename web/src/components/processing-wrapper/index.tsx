import { css, keyframes } from "@emotion/react";
import { FC, PropsWithChildren } from "react";

const moveLTR = keyframes`
  0% {
    transform: translateX(-100%) scaleX(0);
    opacity: .1
  }

  20% {
    transform: translateX(-100%) scaleX(0);
    opacity: .5
  }

  to {
    transform: translateX(0) scaleX(1);
    opacity: 0
  }
`;
export const ProcessingWrapper: FC<
  PropsWithChildren<{ processing: boolean }>
> = ({ children, processing }) => {
  return (
    <div
      css={css`
        position: relative;
        overflow: hidden;
        width: fit-content;
      `}
    >
      <div
        css={css`
          transition: all 0.3s cubic-bezier(0.78, 0.14, 0.15, 0.86);
        `}
      >
        {processing && (
          <div
            css={css`
              position: absolute;
              inset: 0;
              background-color: #fff;
              opacity: 0;
              z-index: 1;
              animation-name: ${moveLTR};
              animation-duration: 2s;
              animation-timing-function: cubic-bezier(0.23, 1, 0.32, 1);
              animation-iteration-count: infinite;
            `}
          />
        )}
        {children}
      </div>
    </div>
  );
};
