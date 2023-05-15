import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon.ts";
import { Col, Empty, Row } from "antd";
import { Link } from "@lepton-dashboard/components/link";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { PopoverDeploymentTable } from "@lepton-dashboard/components/photon-item/components/popover-deployment-table";
import { ExtraInfo } from "@lepton-dashboard/components/photon-item/components/extra-info";
import { VersionDescription } from "@lepton-dashboard/components/photon-item/components/version-description";
import { Actions } from "@lepton-dashboard/components/photon-item/components/actions";
import { TimeDescription } from "@lepton-dashboard/components/photon-item/components/time-description";
import { Description } from "@lepton-dashboard/components/description";

export const PhotonItem: FC<{
  photon?: Photon;
  versions?: PhotonVersion[];
  versionView?: boolean;
  showDetail?: boolean;
  extraActions?: boolean;
}> = ({
  photon,
  versions,
  versionView = false,
  showDetail = false,
  extraActions = false,
}) => {
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
    <Row wrap={false}>
      <Col flex="1 1 auto">
        <Row gutter={[0, 12]}>
          {!versionView && (
            <Col span={24}>
              <Row>
                <Col flex="1 1 auto">
                  <Link
                    css={css`
                      color: ${theme.colorTextHeading};
                    `}
                    to={`/photons/versions/${photon.name}`}
                    relative="route"
                  >
                    <Description.Item
                      css={css`
                        font-weight: 600;
                        font-size: 16px;
                      `}
                      icon={<PhotonIcon />}
                      term={photon.name}
                    />
                  </Link>
                </Col>
                <Col flex="0 0 auto">
                  <Actions photon={photon} extraActions={extraActions} />
                </Col>
              </Row>
            </Col>
          )}
          {!versionView && (
            <Col span={24}>
              <Description.Container>
                <Description.Item description={photon.model} />
              </Description.Container>
            </Col>
          )}
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
                  {!versionView && (
                    <TimeDescription
                      detail={showDetail}
                      photon={photon}
                      versions={versions}
                    />
                  )}
                  {versions && !showDetail && (
                    <VersionDescription photon={photon} versions={versions} />
                  )}
                </Description.Container>
              </Col>

              {versionView && (
                <Col flex="0 0 auto">
                  <Actions photon={photon} extraActions={extraActions} />
                </Col>
              )}
            </Row>
          </Col>

          {showDetail && (
            <ExtraInfo versionView={versionView} photon={photon} />
          )}
        </Row>
      </Col>
    </Row>
  ) : (
    <Empty />
  );
};
