import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { DeploymentItem } from "@lepton-dashboard/routers/workspace/components/deployment-item";
import { PhotonItem } from "@lepton-dashboard/routers/workspace/components/photon-item";
import {
  Col,
  Row,
  Statistic,
  Typography,
  Timeline as AntdTimeline,
} from "antd";
import dayjs from "dayjs";
import { FC } from "react";

export const Timeline: FC<{
  photonGroups: PhotonGroup[];
  deployments: Deployment[];
}> = ({ photonGroups, deployments }) => {
  const theme = useAntdTheme();
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
        id: `photon-${d.name}`,
      };
    }),
  ].sort((a, b) => b.date - a.date);

  return (
    <Row gutter={[16, 24]}>
      <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
        <Card>
          <Statistic
            className="total-photons"
            title="Total Photons"
            value={photonGroups.length}
          />
        </Card>
      </Col>
      <Col flex="1" style={{ maxWidth: "250px", minWidth: "160px" }}>
        <Card>
          <Statistic
            className="total-deployments"
            title="Total Deployments"
            value={deployments.length}
          />
        </Card>
      </Col>
      <Col span={24}>
        <AntdTimeline
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
  );
};
