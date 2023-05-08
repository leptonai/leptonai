import { FC, PropsWithChildren } from "react";
import { Descriptions } from "antd";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";

export const DetailDescription: FC<PropsWithChildren<{ photon: Photon }>> = ({
  photon,
  children,
}) => {
  return (
    <Descriptions bordered size="small" column={1}>
      {children}
      <Descriptions.Item label="Image URL">
        {photon.image || "-"}
      </Descriptions.Item>
      {photon.exposed_ports && (
        <Descriptions.Item label="Exposed Ports">
          {photon.exposed_ports?.join(", ")}
        </Descriptions.Item>
      )}
      {photon.requirement_dependency && (
        <Descriptions.Item label="Requirement Dependency">
          {photon.requirement_dependency?.join(", ")}
        </Descriptions.Item>
      )}
      {photon.container_args && (
        <Descriptions.Item label="Container Args">
          {photon.container_args?.join(", ")}
        </Descriptions.Item>
      )}
      {photon.entrypoint && (
        <Descriptions.Item label="Entrypoint">
          {photon.entrypoint}
        </Descriptions.Item>
      )}
    </Descriptions>
  );
};
