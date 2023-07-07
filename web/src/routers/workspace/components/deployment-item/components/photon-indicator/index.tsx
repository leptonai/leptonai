import { css } from "@emotion/react";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { VersionIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/version-indicator";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { PhotonItem } from "@lepton-dashboard/routers/workspace/components/photon-item";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Popover, Space } from "antd";
import { FC } from "react";

export const PhotonIndicator: FC<{
  photon?: Photon;
  deployment: Deployment;
}> = ({ photon, deployment }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  return (
    <Description.Item
      icon={<PhotonIcon />}
      description={
        photon?.name ? (
          <Space>
            <Popover
              placement="bottomLeft"
              content={
                <div
                  css={css`
                    width: min-content;
                  `}
                >
                  <PhotonItem photon={photon} />
                </div>
              }
            >
              <span>
                <Link
                  to={`/workspace/${workspaceTrackerService.name}/photons/detail/${photon?.id}`}
                >
                  {photon?.name}
                  <VersionIndicator photonId={deployment.photon_id} />
                </Link>
              </span>
            </Popover>
          </Space>
        ) : (
          "-"
        )
      }
    />
  );
};
