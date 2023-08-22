import { FC } from "react";
import { HttpMethods } from "@lepton-libs/open-api-tool";
import { Tag } from "antd";
import { css } from "@emotion/react";

export interface MethodTagProps {
  method: HttpMethods | string;
}
export const MethodTag: FC<MethodTagProps> = ({ method }) => {
  return (
    <Tag
      css={css`
        text-transform: uppercase;
      `}
    >
      {method}
    </Tag>
  );
};
