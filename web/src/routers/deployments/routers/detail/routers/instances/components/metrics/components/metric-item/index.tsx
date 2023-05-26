import { FC, useEffect, useRef } from "react";
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
  const echartRef = useRef<EChartsType | null>(null);
  const deploymentService = useInject(DeploymentService);
  const themeService = useInject(ThemeService);
  const theme = useAntdTheme();
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
          echartRef.current.hideLoading();
          echartRef.current.setOption({
            title: {
              show: data.length === 0,
              textStyle: {
                fontSize: 24,
              },
              text: "No data",
              left: "center",
              top: "center",
            },
            xAxis: {
              show: data.length !== 0,
            },
            yAxis: {
              show: data.length !== 0,
            },
            legend: {
              show: data.length > 1,
              data: data.map((d) => d.metric.handler || d.metric.name),
            },
            series: data.map((d) => {
              return {
                name: d.metric.handler || d.metric.name,
                data: d.values.map(([t, v]) => [t * 1000, +v]),
                type: "line",
                showSymbol: false,
              };
            }),
          });
        }
      },
      error: () => {
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
      echartRef.current.showLoading("default", {
        maskColor: theme.colorBgContainer,
        textColor: theme.colorText,
        text: "Loading ...",
      });
      echartRef.current.setOption({
        legend: {
          type: "scroll",
          orient: "horizontal", // 图例的布局朝向
          bottom: 0, // 图例组件离容器底部的距离
        },
        tooltip: {
          trigger: "axis",
          confine: true,
          valueFormatter: (v: number) => format(v),
        },
        grid: {
          right: 30,
          top: 30,
        },
        xAxis: {
          type: "time",
        },
        yAxis: {
          type: "value",
          axisLabel: {
            formatter: (v: number) => format(v),
          },
        },
        series: [],
      });
    }

    return () => {
      if (echartRef.current) {
        echartRef.current.dispose();
      }
    };
  }, [format, theme.colorBgContainer, theme.colorText, themeService, title]);
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
