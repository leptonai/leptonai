import { FC, useState } from "react";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Metric } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/metric";
import { EChartsType } from "echarts";

export const MetricItem: FC<{
  deploymentId: string;
  metricName: string[];
  description: string[];
  title: string;
  format: (value: number) => string;
  onInit?: (chart: EChartsType) => void;
}> = ({ title, deploymentId, metricName, format, onInit, description }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<
    {
      name: string;
      data: [number, number | null][];
    }[]
  >([]);
  const deploymentService = useInject(DeploymentService);

  useStateFromObservable(
    () => deploymentService.getMetrics(deploymentId, metricName),
    [],
    {
      next: (data) => {
        setData(
          data.map((d) => {
            return {
              name: d.metric.handler || d.metric.name,
              data: d.values.map(([t, v]) => [
                t * 1000,
                v === null ? null : +v,
              ]),
            };
          })
        );
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  return (
    <Metric
      onInit={onInit}
      loading={loading}
      title={title}
      description={description}
      data={data}
      format={format}
    />
  );
};
