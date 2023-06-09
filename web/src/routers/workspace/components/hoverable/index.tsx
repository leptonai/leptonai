import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";

export const Hoverable: FC<PropsWithChildren> = ({ children }) => {
  return (
    <div
      css={css`
        cursor: default;
      `}
    >
      {children}
    </div>
  );
};
