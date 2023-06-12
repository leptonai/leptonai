import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";
import { useInject } from "@lepton-libs/di";
import { FC, useCallback, useMemo, useRef, useState } from "react";
import { Button, Col, Row } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChartLine } from "@carbon/icons-react";
import { Deployment, Instance } from "@lepton-dashboard/interfaces/deployment";
import { MetricItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/components/metrics/components/metric-item";
import { FullScreenDrawer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/components/full-screen-drawer";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { connect, EChartsType } from "echarts";
import { css } from "@emotion/react";

export const MetricsDetail: FC<{
  deploymentId: string;
  instanceId: string;
  gpu: boolean;
}> = ({ deploymentId, instanceId, gpu }) => {
  const metricUtilService = useInject(MetricUtilService);
  const metrics = useMemo(() => {
    const data = [
      {
        name: ["FastAPIQPS", "FastAPIByPathQPS"],
        title: "QPS",
        description: [metricUtilService.getMetricTips("qps")],
        format: metricUtilService.getMetricFormat("qps"),
      },
      {
        name: ["FastAPILatency", "FastAPIByPathLatency"],
        title: "Latency",
        description: [metricUtilService.getMetricTips("latency")],
        format: metricUtilService.getMetricFormat("latency"),
      },
      {
        name: ["memoryUtil", "CPUUtil"],
        title: "CPU & Memory Util",
        description: [
          metricUtilService.getMetricTips("memory"),
          metricUtilService.getMetricTips("cpu"),
        ],
        format: metricUtilService.getMetricFormat("util"),
      },
      {
        name: ["memoryUsage", "memoryTotal"],
        title: "Memory",
        description: [metricUtilService.getMetricTips("memory")],
        format: metricUtilService.getMetricFormat("memory"),
      },
    ];
    if (gpu) {
      data.push(
        {
          name: ["GPUMemoryUtil", "GPUUtil"],
          title: "GPU & GPU Memory Util",
          description: [
            metricUtilService.getMetricTips("gpu"),
            metricUtilService.getMetricTips("gpu_memory"),
          ],

          format: metricUtilService.getMetricFormat("util"),
        },
        {
          name: ["GPUMemoryUsage", "GPUMemoryTotal"],
          title: "GPU Memory",
          description: [metricUtilService.getMetricTips("gpu_memory")],
          format: metricUtilService.getMetricFormat("memory"),
        }
      );
    }
    return data;
  }, [gpu, metricUtilService]);
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
