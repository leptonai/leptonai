import { FC, useEffect, useMemo, useRef } from "react";
import { EChartsType, init } from "echarts";
import { css } from "@emotion/react";
import { useInject } from "@lepton-libs/di";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { debounceTime, fromEvent } from "rxjs";
import { Popover } from "antd";

export const Metric: FC<{
  loading: boolean;
  title: string;
  description: string[];
  data: { name: string; data: [number, number | null][] }[];
  format: (value: number) => string;
  onInit?: (chart: EChartsType) => void;
}> = ({ title, loading, format, data, onInit, description }) => {
  const divRef = useRef<HTMLDivElement | null>(null);
  const onInitRef = useRef(onInit);
  const echartRef = useRef<EChartsType | null>(null);
  const themeService = useInject(ThemeService);
  const theme = useAntdTheme();
  const options = useMemo(
    () => ({
      title: {
        show: data.length === 0,
        textStyle: {
          fontSize: 16,
        },
        text: `No data for ${title}`,
        left: "center",
        top: "center",
      },
      xAxis: {
        type: "time",
        show: data.length !== 0,
        axisLabel: { hideOverlap: true },
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
      series: data.map((d) => ({
        ...d,
        type: "line",
        showSymbol: false,
        connectNulls: true,
      })),
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (v: number) => format(v),
      },
      grid: {
        right: 30,
        top: 10,
        bottom: data.length > 1 ? 50 : 20,
      },
    }),
    [format, data, title]
  );

  useStateFromObservable(
    () => fromEvent(window, "resize").pipe(debounceTime(300)),
    undefined,
    {
      next: () => {
        if (echartRef.current) {
          echartRef.current?.resize();
        }
      },
    }
  );

  useEffect(() => {
    if (divRef.current && !echartRef.current) {
      echartRef.current = init(
        divRef.current,
        themeService.getValidTheme() === "default"
          ? "lepton-light"
          : "lepton-dark"
      );
      if (onInitRef.current) {
        onInitRef.current(echartRef.current);
      }
    }
    if (echartRef.current) {
      if (loading) {
        echartRef.current.showLoading("default", {
          maskColor: theme.colorBgContainer,
          textColor: theme.colorText,
          text: "Loading ...",
        });
      } else {
        echartRef.current.setOption(options);
        echartRef.current?.hideLoading();
      }
    }

    return () => {
      if (echartRef.current) {
        echartRef.current.dispose();
        echartRef.current = null;
      }
    };
  }, [loading, options, theme.colorBgContainer, theme.colorText, themeService]);

  return (
    <div>
      {data.length !== 0 && (
        <div
          css={css`
            color: ${theme.colorTextHeading};
            text-align: center;
            padding-bottom: 6px;
            font-size: 16px;
            font-weight: 500;
            cursor: default;
          `}
        >
          <Popover
            content={
              <div
                css={css`
                  width: 300px;
                  font-size: 12px;
                  display: grid;
                  gap: 1em;
                `}
              >
                {description.map((d) => (
                  <div key={d}>{d}</div>
                ))}
              </div>
            }
          >
            <span>{title}</span>
          </Popover>
        </div>
      )}
      <div
        css={css`
          height: 160px;
          width: 100%;
        `}
        ref={divRef}
      />
    </div>
  );
};
