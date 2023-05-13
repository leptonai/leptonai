import { FC } from "react";
import { Tag } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props.ts";

export const DeploymentStatus: FC<{ status: string } & EmotionProps> = ({
  status,
  className,
}) => {
  return (
    <Tag
      className={className}
      bordered={false}
      color={status === "Running" ? "success" : "processing"}
    >
      {status.toUpperCase()}
    </Tag>
  );
};
