import { FC, useCallback, useRef } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Col, Row } from "antd";
import { Card } from "@lepton-dashboard/components/card";
import { MetricItem } from "@lepton-dashboard/routers/deployments/routers/detail/components/metrics/components/metric-item";
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
];

export const Metrics: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();
  const metricsInstanceRef = useRef(new Map<string, EChartsType>());
  const onInit = useCallback((chart: EChartsType, title: string) => {
    metricsInstanceRef.current.set(title, chart);
    if (metricsInstanceRef.current.size === metrics.length) {
      connect(Array.from(metricsInstanceRef.current.values()));
    }
  }, []);
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
                deploymentId={deployment.id}
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
