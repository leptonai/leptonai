import { useInject } from "@lepton-libs/di";
import { FC, useCallback, useMemo, useRef } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Col, Row } from "antd";
import { Card } from "../../../../../../../../../../components/card";
import { MetricItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/metrics/components/metric-item";
import { connect, EChartsType } from "echarts";
import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";

export const Metrics: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const metricService = useInject(MetricUtilService);
  const metrics = useMemo(
    () => [
      {
        name: ["FastAPIQPS", "FastAPIQPSByPath"],
        title: "QPS",
        description: [metricService.getMetricTips("qps")],
        format: metricService.getMetricFormat("qps"),
      },
      {
        name: ["FastAPILatency", "FastAPILatencyByPath"],
        title: "Latency",
        description: [metricService.getMetricTips("latency")],
        format: metricService.getMetricFormat("latency"),
      },
    ],
    [metricService]
  );

  const theme = useAntdTheme();
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
    <div
      css={css`
        height: 100%;
        padding: 16px;
        overflow: auto;
        background: ${theme.colorBgContainer};
      `}
    >
      <Row gutter={[16, 32]}>
        {metrics.map((m) => (
          <Col key={m.title} sm={24} xs={24} md={12}>
            <Card paddingless overflowShow borderless shadowless>
              <MetricItem
                onInit={(chart) => onInit(chart, m.title)}
                deploymentName={deployment.name}
                metricName={m.name}
                format={m.format}
                title={m.title}
                description={m.description}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};
