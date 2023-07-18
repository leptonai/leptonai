import { FC, useState } from "react";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Metric } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/metric";
import { EChartsType } from "echarts";

export const MetricItem: FC<{
  deploymentId: string;
  replicaId: string;
  metricName: string[];
  title: string;
  description: string[];
  onInit?: (chart: EChartsType) => void;
  format: (value: number) => string;
}> = ({
  title,
  deploymentId,
  replicaId,
  metricName,
  onInit,
  format,
  description,
}) => {
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [data, setData] = useState<
    {
      name: string;
      data: [number, number | null][];
    }[]
  >([]);
  const deploymentService = useInject(DeploymentService);
  useStateFromObservable(
    () =>
      deploymentService.getReplicaMetrics(deploymentId, replicaId, metricName),
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
      error: (err) => {
        setUnavailable(err.response?.status === 500);
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
      unavailable={unavailable}
    />
  );
};
