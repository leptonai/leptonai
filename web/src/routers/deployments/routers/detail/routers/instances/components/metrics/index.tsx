import { FC, useState } from "react";
import { Button, Card, Col, Row } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChartLine } from "@carbon/icons-react";
import { Deployment, Instance } from "@lepton-dashboard/interfaces/deployment";
import { MetricItem } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/metrics/components/metric-item";
import { css } from "@emotion/react";
import prettyBytes from "pretty-bytes";
import { FullScreenDrawer } from "@lepton-dashboard/routers/deployments/components/full-screen-drawer";

const metrics = [
  {
    name: ["FastAPIQPS"],
    title: "QPS",
    format: (v: number) => `${v !== undefined ? v.toFixed(4) : "-"}`,
  },
  {
    name: ["FastAPILatency"],
    title: "Latency",
    format: (v: number) => `${v !== undefined ? v.toFixed(4) : "-"}`,
  },
  {
    name: ["memoryUsage", "memoryTotal"],
    title: "Memory Usage",
    format: (v: number) => prettyBytes(v),
  },
  {
    name: ["CPUUtil"],
    title: "CPU Util",
    format: (v: number) => `${(v * 100).toFixed(2)} %`,
  },
];

const MetricsDetail: FC<{ deploymentId: string; instanceId: string }> = ({
  deploymentId,
  instanceId,
}) => {
  return (
    <div
      css={css`
        height: 100%;
        padding: 16px;
        overflow: auto;
      `}
    >
      <Row gutter={[16, 16]}>
        {metrics.map((m) => (
          <Col key={m.title} sm={24} md={12}>
            <Card>
              <MetricItem
                deploymentId={deploymentId}
                instanceId={instanceId}
                metricName={m.name}
                format={m.format}
                title={m.title}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export const Metrics: FC<{
  deployment: Deployment;
  instance: Instance;
}> = ({ deployment, instance }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        icon={<CarbonIcon icon={<ChartLine />} />}
        type="text"
        size="small"
      >
        Metrics
      </Button>
      <FullScreenDrawer borderless open={open} onClose={() => setOpen(false)}>
        <MetricsDetail deploymentId={deployment.id} instanceId={instance.id} />
      </FullScreenDrawer>
    </>
  );
};
