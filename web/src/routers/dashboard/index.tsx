import { FC, useEffect } from "react";
import styled from "@emotion/styled";
import { Col, Row, Statistic, Timeline, Typography } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";
import { Card } from "@lepton-dashboard/components/card";
import { PhotonGroupCard } from "../../components/photon-group-card";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";
import dayjs from "dayjs";
import { RocketOutlined } from "@ant-design/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { PhotonIcon } from "@lepton-dashboard/components/icons";

const Container = styled.div`
  flex: 1 1 auto;
`;

export const Dashboard: FC = () => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const titleService = useInject(TitleService);
  useEffect(() => {
    titleService.setTitle("Dashboard");
  }, [titleService]);
  const deploymentService = useInject(DeploymentService);
  const groupedPhotons = useStateFromObservable(
    () => photonService.groups(),
    []
  );
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const events = [
    ...groupedPhotons.map((g) => {
      return {
        type: "Photon",
        name: g.name,
        operation: g.data.length > 1 ? "updated" : "created",
        children: (
          <PhotonGroupCard
            deploymentCount={
              deployments.filter((i) =>
                g.data.some((m) => m.id === i.photon_id)
              ).length
            }
            shadowless
            group={g}
          />
        ),
        date: g.latest.created_at,
        id: `photon-${g.name}`,
      };
    }),
    ...deployments.map((d) => {
      return {
        type: "Deployment",
        name: d.name,
        operation: "created",
        children: <DeploymentCard shadowless deployment={d} />,
        date: d.created_at,
        id: `photon-${d.id}`,
      };
    }),
  ].sort((a, b) => b.date - a.date);

  return (
    <Container>
      <Row gutter={[16, 24]}>
        <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
          <Card direction="horizontal">
            <Statistic title="Total Photons" value={groupedPhotons.length} />
          </Card>
        </Col>
        <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
          <Card direction="horizontal">
            <Statistic title="Total Deployments" value={deployments.length} />
          </Card>
        </Col>
        <Col span={24}>
          <Timeline
            css={css`
              .ant-timeline-item-head {
                background: transparent;
              }
            `}
            items={events.map((e) => {
              return {
                color: theme.colorTextSecondary,
                dot:
                  e.type === "Deployment" ? <RocketOutlined /> : <PhotonIcon />,
                children: (
                  <Col key={e.id} span={24}>
                    <Typography.Paragraph
                      style={{ paddingTop: "1px" }}
                      type="secondary"
                    >
                      <Typography.Text type="secondary">
                        {" "}
                        {e.type} {e.operation}{" "}
                      </Typography.Text>
                      <Typography.Text title={dayjs(e.date).format("lll")}>
                        · {dayjs(e.date).fromNow()}
                      </Typography.Text>
                    </Typography.Paragraph>
                    {e.children}
                  </Col>
                ),
              };
            })}
          />
        </Col>
      </Row>
    </Container>
  );
};
