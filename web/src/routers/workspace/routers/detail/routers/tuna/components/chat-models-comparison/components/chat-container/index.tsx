import { FC, PropsWithChildren, ReactNode } from "react";
import { css } from "@emotion/react";

export const ChatContainer: FC<PropsWithChildren & { header: ReactNode }> = ({
  header,
  children,
}) => {
  return (
    <div
      css={css`
        display: flex;
        flex-direction: column;
        height: 100%;
        width: 100%;
      `}
    >
      <div
        css={css`
          flex: 0;
        `}
      >
        {header}
      </div>
      <div
        css={css`
          flex: 1;
          overflow: hidden;
        `}
      >
        {children}
      </div>
    </div>
  );
};
