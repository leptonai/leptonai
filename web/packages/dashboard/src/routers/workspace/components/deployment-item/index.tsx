import { CreateDeployment } from "@lepton-dashboard/routers/workspace/components/create-deployment";
import { DeleteDeployment } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/delete-deployment";
import { HardwareIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/hardware-indicator";
import { PhotonIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/photon-indicator";
import { Storage } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/storage";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { FC, useMemo } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Col, Divider, Row, Space } from "antd";
import { css } from "@emotion/react";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Replicate, Time } from "@carbon/icons-react";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/components/deployment-status";
import { DateParser } from "../../../../components/date-parser";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { EditDeployment } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/edit-deployment";
import { Envs } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/envs";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { EndpointIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/endpoint-indicator";

export const DeploymentItem: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const photons = useStateFromBehaviorSubject(photonService.list());
  const photon = useMemo(() => {
    return photons.find((p) => p.id === deployment.photon_id);
  }, [deployment.photon_id, photons]);

  return (
    <Row gutter={[16, 8]}>
      <Col span={24}>
        <Row
          gutter={16}
          css={css`
            height: 28px;
            overflow: hidden;
          `}
        >
          <Col flex="1 1 auto">
            <LinkTo
              css={css`
                color: ${theme.colorTextHeading};
              `}
              icon={
                <DeploymentStatus
                  deploymentName={deployment.name}
                  status={deployment.status.state}
                />
              }
              name="deploymentDetail"
              params={{ deploymentName: deployment.name }}
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                term={deployment.name}
              />
            </LinkTo>
          </Col>
          <Col flex="0 0 auto">
            <Space size={0} split={<Divider type="vertical" />}>
              <CreateDeployment fork={deployment} />
              <EditDeployment deployment={deployment} />
              <DeleteDeployment deployment={deployment} />
            </Space>
          </Col>
        </Row>
      </Col>
      <Col span={24}>
        <Row gutter={[16, 4]}>
          <Col flex="0 0 400px">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Space>
                  <PhotonIndicator photon={photon} deployment={deployment} />
                  <HardwareIndicator
                    shape={deployment.resource_requirement.resource_shape}
                  />
                </Space>
              </Col>
              <Col span={24}>
                <Description.Container>
                  <EndpointIndicator
                    endpoint={deployment.status.endpoint.external_endpoint}
                  />
                </Description.Container>
              </Col>
            </Row>
          </Col>
          <Col flex="0 0 400px">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Container>
                  <Description.Item
                    icon={<CarbonIcon icon={<Replicate />} />}
                    description={
                      <LinkTo
                        name="deploymentDetailReplicasList"
                        params={{ deploymentName: deployment.name }}
                      >
                        {deployment.resource_requirement.min_replicas}
                        {deployment.resource_requirement.min_replicas > 1
                          ? " replicas"
                          : " replica"}
                      </LinkTo>
                    }
                  />
                  {deployment.mounts && deployment.mounts.length > 0 ? (
                    <Storage mounts={deployment.mounts} />
                  ) : null}
                  {deployment.envs && deployment.envs.length > 0 ? (
                    <Envs envs={deployment.envs} />
                  ) : null}
                </Description.Container>
              </Col>
              <Col span={24}>
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <DateParser
                      prefix="Created at "
                      date={deployment.created_at}
                    />
                  }
                />
              </Col>
            </Row>
          </Col>
        </Row>
      </Col>
    </Row>
  );
};
