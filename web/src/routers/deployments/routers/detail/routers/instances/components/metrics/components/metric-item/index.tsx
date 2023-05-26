import { FC, useEffect, useMemo, useRef, useState } from "react";
import { EChartsType, init } from "echarts";
import { css } from "@emotion/react";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { ThemeService } from "@lepton-dashboard/services/theme.service";

export const MetricItem: FC<{
  deploymentId: string;
  instanceId: string;
  metricName: string[];
  title: string;
  format: (value: number) => string;
}> = ({ title, deploymentId, instanceId, metricName, format }) => {
  const divRef = useRef<HTMLDivElement | null>(null);
  const loadingRef = useRef(true);
  const [data, setData] = useState<
    {
      name: string;
      data: [number, number][];
      type: string;
      showSymbol: boolean;
    }[]
  >([]);
  const echartRef = useRef<EChartsType | null>(null);
  const deploymentService = useInject(DeploymentService);
  const themeService = useInject(ThemeService);
  const theme = useAntdTheme();
  const options = useMemo(
    () => ({
      title: {
        show: data.length === 0,
        textStyle: {
          fontSize: 16,
        },
        text: "No data",
        left: "center",
        top: "center",
      },
      xAxis: {
        type: "time",
        show: data.length !== 0,
      },
      yAxis: {
        type: "value",
        show: data.length !== 0,
        axisLabel: {
          formatter: (v: number) => format(v),
        },
      },
      legend: {
        show: data.length > 1,
        data: data.map((d) => d.name),
        type: "scroll",
        orient: "horizontal",
        bottom: 0,
      },
      series: data,
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (v: number) => format(v),
      },
      grid: {
        right: 30,
        top: 30,
      },
    }),
    [format, data]
  );
  useStateFromObservable(
    () =>
      deploymentService.getInstanceMetrics(
        deploymentId,
        instanceId,
        metricName
      ),
    [],
    {
      next: (data) => {
        if (echartRef.current) {
          loadingRef.current = false;
          echartRef.current.hideLoading();
          setData(
            data.map((d) => {
              return {
                name: d.metric.handler || d.metric.name,
                data: d.values.map(([t, v]) => [t * 1000, +v]),
                type: "line",
                showSymbol: false,
              };
            })
          );
          echartRef.current.setOption(options);
        }
      },
      error: () => {
        loadingRef.current = false;
        if (echartRef.current) {
          echartRef.current.hideLoading();
        }
      },
    }
  );

  useEffect(() => {
    if (divRef.current) {
      echartRef.current = init(
        divRef.current,
        themeService.getValidTheme() === "default"
          ? "lepton-light"
          : "lepton-dark"
      );
      if (loadingRef.current) {
        echartRef.current.showLoading("default", {
          maskColor: theme.colorBgContainer,
          textColor: theme.colorText,
          text: "Loading ...",
        });
      }
      echartRef.current.setOption(options);
    }

    return () => {
      if (echartRef.current) {
        echartRef.current.dispose();
      }
    };
  }, [format, themeService, theme, title, options]);
  return (
    <div>
      <div
        css={css`
          color: ${theme.colorTextHeading};
          text-align: center;
          padding-bottom: 12px;
          font-size: 16px;
          font-weight: 500;
        `}
      >
        {title}
      </div>
      <div
        css={css`
          height: 220px;
          width: 100%;
        `}
        ref={divRef}
      />
    </div>
  );
};
