import { FC } from "react";
import { Tag } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { css } from "@emotion/react";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";

export const DeploymentStatus: FC<{ status: string } & EmotionProps> = ({
  status,
  className,
}) => {
  return (
    <Tag
      className={className}
      bordered={false}
      css={css`
        margin-inline: 0;
        font-weight: 500;
      `}
      icon={<DeploymentIcon />}
      color={status === "Running" ? "success" : "processing"}
    >
      {status.toUpperCase()}
    </Tag>
  );
};
