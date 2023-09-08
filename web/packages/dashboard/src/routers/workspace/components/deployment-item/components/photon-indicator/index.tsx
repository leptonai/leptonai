import { css } from "@emotion/react";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { PhotonItem } from "@lepton-dashboard/routers/workspace/components/photon-item";
import { PhotonLabel } from "@lepton-dashboard/routers/workspace/components/photon-label";
import { Popover, Space } from "antd";
import { FC } from "react";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const PhotonIndicator: FC<{
  photon?: Photon;
  deployment: Deployment;
}> = ({ photon, deployment }) => {
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
                <LinkTo
                  name="photonDetail"
                  params={{
                    photonId: photon?.id,
                  }}
                >
                  <PhotonLabel
                    name={photon.name}
                    created_at={photon.created_at}
                    id={deployment.photon_id}
                    showTime={false}
                    showName
                  />
                </LinkTo>
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
