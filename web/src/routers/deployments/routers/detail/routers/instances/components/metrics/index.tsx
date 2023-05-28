import { FC, useCallback, useRef, useState } from "react";
import { Button, Col, Row } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChartLine } from "@carbon/icons-react";
import { Deployment, Instance } from "@lepton-dashboard/interfaces/deployment";
import { MetricItem } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/metrics/components/metric-item";
import prettyBytes from "pretty-bytes";
import { FullScreenDrawer } from "@lepton-dashboard/routers/deployments/components/full-screen-drawer";
import { Card } from "@lepton-dashboard/components/card";
import { connect, EChartsType } from "echarts";

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

export const MetricsDetail: FC<{
  deploymentId: string;
  instanceId: string;
}> = ({ deploymentId, instanceId }) => {
  const metricsInstanceRef = useRef(new Map<string, EChartsType>());
  const onInit = useCallback((chart: EChartsType, title: string) => {
    metricsInstanceRef.current.set(title, chart);
    if (metricsInstanceRef.current.size === metrics.length) {
      connect(Array.from(metricsInstanceRef.current.values()));
    }
  }, []);
  return (
    <Card borderless shadowless>
      <Row gutter={[16, 32]}>
        {metrics.map((m) => (
          <Col key={m.title} sm={24} xs={24} md={12}>
            <Card paddingless overflowShow borderless shadowless>
              <MetricItem
                onInit={(chart) => onInit(chart, m.title)}
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
    </Card>
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
