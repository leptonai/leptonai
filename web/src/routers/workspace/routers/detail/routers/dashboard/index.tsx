import { FC, useEffect } from "react";
import styled from "@emotion/styled";
import { Col, Row, Statistic, Timeline, Typography } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import dayjs from "dayjs";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { DeploymentIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import { PhotonItem } from "../../../../components/photon-item";
import { DeploymentItem } from "../../../../components/deployment-item";

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
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const events = [
    ...photonGroups.map((g) => {
      return {
        type: "Photon",
        name: g.name,
        operation: g.versions.length > 1 ? "updated" : "created",
        children: (
          <Card>
            <PhotonItem photon={g} versions={g.versions} />
          </Card>
        ),
        date: g.created_at,
        id: `photon-${g.name}`,
      };
    }),
    ...deployments.map((d) => {
      return {
        type: "Deployment",
        name: d.name,
        operation: "created",
        children: (
          <Card>
            <DeploymentItem deployment={d} />
          </Card>
        ),
        date: d.created_at,
        id: `photon-${d.id}`,
      };
    }),
  ].sort((a, b) => b.date - a.date);

  return (
    <Container>
      <Row gutter={[16, 24]}>
        <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
          <Card>
            <Statistic title="Total Photons" value={photonGroups.length} />
          </Card>
        </Col>
        <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
          <Card>
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
                  e.type === "Deployment" ? <DeploymentIcon /> : <PhotonIcon />,
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
