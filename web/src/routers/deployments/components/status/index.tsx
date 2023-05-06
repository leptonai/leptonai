import { FC } from "react";
import { Badge } from "antd";

export const Status: FC<{ status: string }> = ({ status }) => {
  return (
    <Badge
      status={status === "running" ? "success" : "processing"}
      text={status.toUpperCase()}
    />
  );
};
