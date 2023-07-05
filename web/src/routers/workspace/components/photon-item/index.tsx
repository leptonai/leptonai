import { WatsonHealth3DSoftware } from "@carbon/icons-react";
import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Col, Empty, Row } from "antd";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { CarbonIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
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
import { WorkspaceTrackerService } from "../../services/workspace-tracker.service";

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
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
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
            <Link
              css={css`
                color: ${theme.colorTextHeading};
              `}
              to={
                showDetail
                  ? `/workspace/${workspaceTrackerService.name}/photons/detail/${photon.id}`
                  : `/workspace/${workspaceTrackerService.name}/photons/versions/${photon.name}`
              }
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                icon={
                  showDetail ? (
                    <CarbonIcon icon={<WatsonHealth3DSoftware />} />
                  ) : (
                    <PhotonIcon />
                  )
                }
                term={showDetail ? photon.id : photon.name}
              />
            </Link>
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
              extraActions={extraActions}
            />
          </Col>
        </Row>
      </Col>
      {!versionView && (
        <Col span={24}>
          <Description.Item description={photon.model} />
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
        </Row>
      </Col>
      {showDetail && <ExtraInfo versionView={versionView} photon={photon} />}
    </Row>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No photon found" />
  );
};
