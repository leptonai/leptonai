import { FC, useCallback, useMemo, useRef, useState } from "react";
import { Button, Col, Row } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChartLine } from "@carbon/icons-react";
import { Deployment, Instance } from "@lepton-dashboard/interfaces/deployment";
import { MetricItem } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/metrics/components/metric-item";
import { FullScreenDrawer } from "@lepton-dashboard/routers/deployments/components/full-screen-drawer";
import { Card } from "@lepton-dashboard/components/card";
import { connect, EChartsType } from "echarts";
import { css } from "@emotion/react";
import { MetricUtilService } from "@lepton-dashboard/services/metric-util.service";

export const MetricsDetail: FC<{
  deploymentId: string;
  instanceId: string;
  gpu: boolean;
}> = ({ deploymentId, instanceId, gpu }) => {
  const metrics = useMemo(() => {
    const data = [
      {
        name: ["FastAPIQPS", "FastAPIByPathQPS"],
        title: "QPS",
        description: [MetricUtilService.getMetricTips("qps")],
        format: MetricUtilService.getMetricFormat("qps"),
      },
      {
        name: ["FastAPILatency", "FastAPIByPathLatency"],
        title: "Latency",
        description: [MetricUtilService.getMetricTips("latency")],
        format: MetricUtilService.getMetricFormat("latency"),
      },
      {
        name: ["memoryUtil", "CPUUtil"],
        title: "CPU & Memory Util",
        description: [
          MetricUtilService.getMetricTips("memory"),
          MetricUtilService.getMetricTips("cpu"),
        ],
        format: MetricUtilService.getMetricFormat("util"),
      },
      {
        name: ["memoryUsage", "memoryTotal"],
        title: "Memory",
        description: [MetricUtilService.getMetricTips("memory")],
        format: MetricUtilService.getMetricFormat("memory"),
      },
    ];
    if (gpu) {
      data.push(
        {
          name: ["GPUMemoryUtil", "GPUUtil"],
          title: "GPU & GPU Memory Util",
          description: [
            MetricUtilService.getMetricTips("gpu"),
            MetricUtilService.getMetricTips("gpu_memory"),
          ],

          format: MetricUtilService.getMetricFormat("util"),
        },
        {
          name: ["GPUMemoryUsage", "GPUMemoryTotal"],
          title: "GPU Memory",
          description: [MetricUtilService.getMetricTips("gpu_memory")],
          format: MetricUtilService.getMetricFormat("memory"),
        }
      );
    }
    return data;
  }, [gpu]);
  const metricsInstanceRef = useRef(new Map<string, EChartsType>());
  const onInit = useCallback(
    (chart: EChartsType, title: string) => {
      metricsInstanceRef.current.set(title, chart);
      if (metricsInstanceRef.current.size === metrics.length) {
        connect(Array.from(metricsInstanceRef.current.values()));
      }
    },
    [metrics.length]
  );
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
                description={m.description}
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
        <div
          css={css`
            height: 100%;
            overflow: auto;
          `}
        >
          <MetricsDetail
            gpu={!!deployment.resource_requirement.accelerator_num}
            deploymentId={deployment.id}
            instanceId={instance.id}
          />
        </div>
      </FullScreenDrawer>
    </>
  );
};
