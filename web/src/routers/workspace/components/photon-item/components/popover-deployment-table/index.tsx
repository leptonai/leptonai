import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { ProcessingWrapper } from "@lepton-dashboard/components/processing-wrapper";
import { DeploymentMinTable } from "@lepton-dashboard/routers/workspace/components/deployment-min-table";
import { FC, useMemo } from "react";
import { Popover, Tag } from "antd";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { css } from "@emotion/react";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const PopoverDeploymentTable: FC<{
  photon: Photon;
  deployments: Deployment[];
}> = ({ photon, deployments }) => {
  const color = useMemo(() => {
    const running = deployments.every((d) => d.status.state === "Running");
    if (deployments.length > 0) {
      return running ? "success" : "processing";
    } else {
      return "default";
    }
  }, [deployments]);
  return (
    <MinThemeProvider>
      <ProcessingWrapper processing={color === "processing"}>
        <Tag
          color={color}
          css={css`
            margin-right: 0;
          `}
        >
          <Description.Item
            icon={<DeploymentIcon />}
            description={
              <Popover
                open={deployments.length > 0 ? undefined : false}
                placement="bottomLeft"
                content={<DeploymentMinTable deployments={deployments} />}
              >
                <span>
                  <LinkTo
                    name="deploymentsList"
                    params={{
                      photonName: photon.name,
                    }}
                    relative="route"
                  >
                    {deployments.length > 0 ? deployments.length : "No"}{" "}
                    {deployments.length > 1 ? "deployments" : "deployment"}
                  </LinkTo>
                </span>
              </Popover>
            }
          />
        </Tag>
      </ProcessingWrapper>
    </MinThemeProvider>
  );
};
