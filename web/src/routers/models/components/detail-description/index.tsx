import { FC, PropsWithChildren } from "react";
import { Descriptions } from "antd";
import { Model } from "@lepton-dashboard/interfaces/model.ts";

export const DetailDescription: FC<PropsWithChildren<{ model: Model }>> = ({
  model,
  children,
}) => {
  return (
    <Descriptions bordered size="small" column={1}>
      {children}
      <Descriptions.Item label="Image URL">
        {model.image_url || "-"}
      </Descriptions.Item>
      {model.exposed_ports && (
        <Descriptions.Item label="Exposed Ports">
          {model.exposed_ports?.join(", ")}
        </Descriptions.Item>
      )}
      {model.requirement_dependency && (
        <Descriptions.Item label="Requirement Dependency">
          {model.requirement_dependency?.join(", ")}
        </Descriptions.Item>
      )}
      {model.container_args && (
        <Descriptions.Item label="Container Args">
          {model.container_args?.join(", ")}
        </Descriptions.Item>
      )}
      {model.entrypoint && (
        <Descriptions.Item label="Entrypoint">
          {model.entrypoint}
        </Descriptions.Item>
      )}
    </Descriptions>
  );
};
