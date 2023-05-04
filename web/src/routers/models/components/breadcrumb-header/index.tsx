import { FC, PropsWithChildren } from "react";
import { Card } from "antd";
import { css } from "@emotion/react";

export const BreadcrumbHeader: FC<PropsWithChildren> = ({ children }) => {
  return (
    <Card
      size="small"
      css={css`
        margin-bottom: 24px;
        padding: 0 12px;
      `}
    >
      {children}
    </Card>
  );
};
