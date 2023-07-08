import { CopyFile } from "@carbon/icons-react";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { PopoverDeploymentTable } from "@lepton-dashboard/routers/workspace/components/photon-item/components/popover-deployment-table";
import { FC } from "react";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { Descriptions, Typography } from "antd";

export const ExtraInfo: FC<{
  photon: Photon;
  deployments: Deployment[];
}> = ({ photon, deployments }) => {
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
      }}
    >
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="Created at">
          <Typography.Text
            copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
          >
            <DateParser detail date={photon.created_at} />
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Model">
          <Typography.Text
            copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
          >
            {photon.model}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Deployments">
          <PopoverDeploymentTable photon={photon} deployments={deployments} />
        </Descriptions.Item>
        {photon.container_args && photon.container_args.length && (
          <Descriptions.Item label="Arguments">
            <Typography.Text
              copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
            >
              {photon.container_args?.join(", ")}
            </Typography.Text>
          </Descriptions.Item>
        )}
        {photon.requirement_dependency &&
          photon.requirement_dependency.length && (
            <Descriptions.Item label="Requirements depedency">
              {photon.requirement_dependency?.map((d) => (
                <div key={d}>{d}</div>
              ))}
            </Descriptions.Item>
          )}
        {photon.system_dependency && photon.system_dependency.length && (
          <Descriptions.Item label="System dendency">
            {photon.system_dependency?.map((d) => (
              <div key={d}>{d}</div>
            ))}
          </Descriptions.Item>
        )}
        {photon.entrypoint && (
          <Descriptions.Item label="Entrypoint">
            <Typography.Text
              copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
            >
              {photon.entrypoint}
            </Typography.Text>
          </Descriptions.Item>
        )}
        {photon.exposed_ports && photon.exposed_ports.length && (
          <Descriptions.Item label="Exposed ports">
            <Typography.Text
              copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
            >
              {photon.exposed_ports?.join(", ")}
            </Typography.Text>
          </Descriptions.Item>
        )}
        {photon.image && (
          <Descriptions.Item label="Image URL">
            <Typography.Text
              copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
            >
              {photon.image}
            </Typography.Text>
          </Descriptions.Item>
        )}
      </Descriptions>
    </ThemeProvider>
  );
};
