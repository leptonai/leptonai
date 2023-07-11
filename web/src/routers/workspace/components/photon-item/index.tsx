import { PhotonLabel } from "@lepton-dashboard/routers/workspace/components/photon-label";
import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Col, Empty, Row } from "antd";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { PopoverDeploymentTable } from "@lepton-dashboard/routers/workspace/components/photon-item/components/popover-deployment-table";
import { ExtraInfo } from "@lepton-dashboard/routers/workspace/components/photon-item/components/extra-info";
import { VersionDescription } from "@lepton-dashboard/routers/workspace/components/photon-item/components/version-description";
import { Actions } from "@lepton-dashboard/routers/workspace/components/photon-item/components/actions";
import { TimeDescription } from "@lepton-dashboard/routers/workspace/components/photon-item/components/time-description";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const PhotonItem: FC<{
  photon?: Photon;
  versions?: PhotonVersion[];
  showDetail?: boolean;
}> = ({ photon, versions, showDetail = false }) => {
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const relatedDeployments = deployments.filter((d) => {
    if (versions) {
      return versions.some((v) => v.id === d.photon_id);
    } else {
      return d.photon_id === photon?.id;
    }
  });
  return photon ? (
    <Row gutter={[0, 12]}>
      <Col span={24}>
        <Row gutter={[0, 12]}>
          <Col flex="1 1 auto">
            <LinkTo
              css={css`
                color: ${theme.colorTextHeading};
              `}
              name={showDetail ? "photonDetail" : "photonVersions"}
              params={
                showDetail
                  ? {
                      photonId: photon.id,
                    }
                  : {
                      photonId: photon.name,
                    }
              }
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                icon={showDetail ? null : <PhotonIcon />}
                term={
                  showDetail ? (
                    <PhotonLabel
                      showName
                      id={photon.id}
                      name={photon.name}
                      created_at={photon.created_at}
                    />
                  ) : (
                    photon.name
                  )
                }
              />
            </LinkTo>
          </Col>
          <Col
            flex="0 0 auto"
            css={css`
              position: relative;
              left: -6px;
            `}
          >
            <Actions
              relatedDeployments={relatedDeployments}
              photon={photon}
              extraActions={showDetail}
            />
          </Col>
        </Row>
      </Col>
      {showDetail ? (
        <Col span={24}>
          <ExtraInfo deployments={relatedDeployments} photon={photon} />
        </Col>
      ) : (
        <>
          <Col span={24}>
            <Description.Item description={photon.model} />
          </Col>
          <Col span={24}>
            <Row>
              <Col flex="1 1 auto">
                <Description.Container
                  css={css`
                    font-size: 12px;
                  `}
                >
                  <PopoverDeploymentTable
                    photon={photon}
                    deployments={relatedDeployments}
                  />
                  <TimeDescription
                    detail={showDetail}
                    photon={photon}
                    versions={versions}
                  />
                  {versions && (
                    <VersionDescription photon={photon} versions={versions} />
                  )}
                </Description.Container>
              </Col>
            </Row>
          </Col>
        </>
      )}
    </Row>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No photon found" />
  );
};
