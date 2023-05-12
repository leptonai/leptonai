import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import {
  Breadcrumb,
  Col,
  List as AntdList,
  Row,
  Timeline,
  Typography,
} from "antd";
import { Link } from "@lepton-dashboard/components/link";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/photons/components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { PhotonCard } from "@lepton-dashboard/components/photon-card";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import dayjs from "dayjs";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { PhotonIcon } from "@lepton-dashboard/components/icons";

export const Versions: FC = () => {
  const { name } = useParams();
  const photonService = useInject(PhotonService);
  const photons = useStateFromObservable(
    () => photonService.listByName(name!),
    []
  );
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const filteredDeployments = useMemo(() => {
    const ids = photons.filter((m) => m.name === name).map((i) => i.id);
    return deployments.filter((d) => ids.indexOf(d.photon_id) !== -1);
  }, [deployments, name, photons]);

  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
            items={[
              {
                title: (
                  <>
                    <PhotonIcon />
                    <Link to="../../photons">
                      <span>Photons</span>
                    </Link>
                  </>
                ),
              },
              {
                title: name,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Version History">
          <Timeline
            css={css`
              padding: 8px 0;
            `}
            items={photons.map((m) => {
              return {
                key: m.id,
                color: theme.colorTextSecondary,
                dot: <PhotonIcon />,
                children: (
                  <Col key={m.id} span={24}>
                    <Typography.Paragraph
                      style={{ paddingTop: "1px" }}
                      type="secondary"
                    >
                      Created at {dayjs(m.created_at).format("lll")}
                    </Typography.Paragraph>
                    <PhotonCard action={true} shadowless={true} photon={m} />
                  </Col>
                ),
              };
            })}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Deployments" paddingless>
          <AntdList
            itemLayout="horizontal"
            dataSource={filteredDeployments}
            renderItem={(deployment) => (
              <AntdList.Item style={{ padding: 0, display: "block" }}>
                <DeploymentCard photonPage deployment={deployment} borderless />
              </AntdList.Item>
            )}
          />
        </Card>
      </Col>
    </Row>
  );
};
