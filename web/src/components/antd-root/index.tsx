import { css } from "@emotion/react";
import { App } from "antd";
import { FC, PropsWithChildren } from "react";

export const AntdRoot: FC<PropsWithChildren> = ({ children }) => {
  return (
    <App
      notification={{ maxCount: 1 }}
      css={css`
        height: 100%;
      `}
    >
      {children}
    </App>
  );
};
