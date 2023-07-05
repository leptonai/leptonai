import { BreadcrumbProps } from "antd/es/breadcrumb/Breadcrumb";
import { FC } from "react";
import { Card } from "../../../../components/card";
import { Breadcrumb } from "antd";
import { css } from "@emotion/react";

export const BreadcrumbHeader: FC<BreadcrumbProps> = ({ items }) => {
  return (
    <Card
      paddingless
      css={css`
        padding: 6px 16px;
      `}
    >
      <Breadcrumb items={items} />
    </Card>
  );
};
