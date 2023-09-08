import { useEffect } from "react";
import { registerTheme } from "echarts";

const lightTheme = {
  color: [
    "#5B8FF9",
    "#5AD8A6",
    "#5D7092",
    "#F6BD16",
    "#6F5EF9",
    "#6DC8EC",
    "#945FB9",
    "#FF9845",
    "#1E9493",
    "#FF99C3",
  ],
  backgroundColor: "transparent",
  textStyle: {},
  title: {
    textStyle: {
      color: "#464646",
    },
    subtextStyle: {
      color: "#6E7079",
    },
  },
  line: {
    itemStyle: {
      borderWidth: 1,
    },
    lineStyle: {
      width: 1.5,
    },
    symbolSize: 4,
    symbol: "roundRect",
    smooth: false,
  },
  radar: {
    itemStyle: {
      borderWidth: 1,
    },
    lineStyle: {
      width: 1.5,
    },
    symbolSize: 4,
    symbol: "roundRect",
    smooth: false,
  },
  bar: {
    itemStyle: {
      barBorderWidth: 0,
      barBorderColor: "#ccc",
    },
  },
  pie: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  scatter: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  boxplot: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  parallel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  sankey: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  funnel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  gauge: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  candlestick: {
    itemStyle: {
      color: "#eb5454",
      color0: "#47b262",
      borderColor: "#eb5454",
      borderColor0: "#47b262",
      borderWidth: 1,
    },
  },
  graph: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
    lineStyle: {
      width: 1,
      color: "#aaa",
    },
    symbolSize: 4,
    symbol: "roundRect",
    smooth: false,
    color: [
      "#5470c6",
      "#91cc75",
      "#fac858",
      "#ee6666",
      "#73c0de",
      "#3ba272",
      "#fc8452",
      "#9a60b4",
      "#ea7ccc",
    ],
    label: {
      color: "#eee",
    },
  },
  map: {
    itemStyle: {
      areaColor: "#eee",
      borderColor: "#444",
      borderWidth: 0.5,
    },
    label: {
      color: "#000",
    },
    emphasis: {
      itemStyle: {
        areaColor: "rgba(255,215,0,0.8)",
        borderColor: "#444",
        borderWidth: 1,
      },
      label: {
        color: "rgb(100,0,0)",
      },
    },
  },
  geo: {
    itemStyle: {
      areaColor: "#eee",
      borderColor: "#444",
      borderWidth: 0.5,
    },
    label: {
      color: "#000",
    },
    emphasis: {
      itemStyle: {
        areaColor: "rgba(255,215,0,0.8)",
        borderColor: "#444",
        borderWidth: 1,
      },
      label: {
        color: "rgb(100,0,0)",
      },
    },
  },
  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisLabel: {
      show: true,
      color: "#6E7079",
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: ["#E0E6F1"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["rgba(250,250,250,0.2)", "rgba(210,219,238,0.2)"],
      },
    },
  },
  valueAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisLabel: {
      show: true,
      color: "#6E7079",
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: ["#eee"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["rgba(250,250,250,0.2)", "rgba(210,219,238,0.2)"],
      },
    },
  },
  logAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisLabel: {
      show: true,
      color: "#6E7079",
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: ["#E0E6F1"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["rgba(250,250,250,0.2)", "rgba(210,219,238,0.2)"],
      },
    },
  },
  timeAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#6E7079",
      },
    },
    axisLabel: {
      show: true,
      color: "#6E7079",
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: ["#E0E6F1"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["rgba(250,250,250,0.2)", "rgba(210,219,238,0.2)"],
      },
    },
  },
  toolbox: {
    iconStyle: {
      borderColor: "#999",
    },
    emphasis: {
      iconStyle: {
        borderColor: "#666",
      },
    },
  },
  legend: {
    textStyle: {
      color: "#333",
    },
  },
  tooltip: {
    axisPointer: {
      lineStyle: {
        color: "#ccc",
        width: 1,
      },
      crossStyle: {
        color: "#ccc",
        width: 1,
      },
    },
  },
  timeline: {
    lineStyle: {
      color: "#DAE1F5",
      width: 2,
    },
    itemStyle: {
      color: "#A4B1D7",
      borderWidth: 1,
    },
    controlStyle: {
      color: "#A4B1D7",
      borderColor: "#A4B1D7",
      borderWidth: 1,
    },
    checkpointStyle: {
      color: "#316bf3",
      borderColor: "fff",
    },
    label: {
      color: "#A4B1D7",
    },
    emphasis: {
      itemStyle: {
        color: "#FFF",
      },
      controlStyle: {
        color: "#A4B1D7",
        borderColor: "#A4B1D7",
        borderWidth: 1,
      },
      label: {
        color: "#A4B1D7",
      },
    },
  },
  visualMap: {
    color: ["#bf444c", "#d88273", "#f6efa6"],
  },
  dataZoom: {
    handleSize: "undefined%",
    textStyle: {},
  },
  markPoint: {
    label: {
      color: "#eee",
    },
    emphasis: {
      label: {
        color: "#eee",
      },
    },
  },
};
const darkTheme = {
  color: [
    "#5B8FF9",
    "#5AD8A6",
    "#5D7092",
    "#F6BD16",
    "#6F5EF9",
    "#6DC8EC",
    "#945FB9",
    "#FF9845",
    "#1E9493",
    "#FF99C3",
  ],
  backgroundColor: "transparent",
  textStyle: {},
  title: {
    textStyle: {
      color: "#555",
    },
    subtextStyle: {
      color: "#aaaaaa",
    },
  },
  line: {
    itemStyle: {
      borderWidth: 1,
    },
    lineStyle: {
      width: 1.5,
    },
    symbolSize: 4,
    symbol: "roundRect",
    smooth: false,
  },
  radar: {
    itemStyle: {
      borderWidth: 1,
    },
    lineStyle: {
      width: 1.5,
    },
    symbolSize: 4,
    symbol: "circle",
    smooth: false,
  },
  bar: {
    itemStyle: {
      barBorderWidth: 0,
      barBorderColor: "#ccc",
    },
  },
  pie: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  scatter: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  boxplot: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  parallel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  sankey: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  funnel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  gauge: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
  },
  candlestick: {
    itemStyle: {
      color: "#fd1050",
      color0: "#0cf49b",
      borderColor: "#fd1050",
      borderColor0: "#0cf49b",
      borderWidth: 1,
    },
  },
  graph: {
    itemStyle: {
      borderWidth: 0,
      borderColor: "#ccc",
    },
    lineStyle: {
      width: 1,
      color: "#aaa",
    },
    symbolSize: 4,
    symbol: "circle",
    smooth: false,
    color: [
      "#5B8FF9",
      "#5AD8A6",
      "#5D7092",
      "#F6BD16",
      "#6F5EF9",
      "#6DC8EC",
      "#945FB9",
      "#FF9845",
      "#1E9493",
      "#FF99C3",
    ],
    label: {
      color: "#eee",
    },
  },
  map: {
    itemStyle: {
      areaColor: "#eee",
      borderColor: "#444",
      borderWidth: 0.5,
    },
    label: {
      color: "#000",
    },
    emphasis: {
      itemStyle: {
        areaColor: "rgba(255,215,0,0.8)",
        borderColor: "#444",
        borderWidth: 1,
      },
      label: {
        color: "rgb(100,0,0)",
      },
    },
  },
  geo: {
    itemStyle: {
      areaColor: "#eee",
      borderColor: "#444",
      borderWidth: 0.5,
    },
    label: {
      color: "#000",
    },
    emphasis: {
      itemStyle: {
        areaColor: "rgba(255,215,0,0.8)",
        borderColor: "#444",
        borderWidth: 1,
      },
      label: {
        color: "rgb(100,0,0)",
      },
    },
  },
  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisLabel: {
      show: true,
      color: "#555",
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: ["#aaaaaa"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["#555"],
      },
    },
  },
  valueAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisLabel: {
      show: true,
      color: "#555",
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: ["#21262d"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["#555"],
      },
    },
  },
  logAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisLabel: {
      show: true,
      color: "#555",
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: ["#aaaaaa"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["#555"],
      },
    },
  },
  timeAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: "#555",
      },
    },
    axisLabel: {
      show: true,
      color: "#555",
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: ["#aaaaaa"],
      },
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: ["#555"],
      },
    },
  },
  toolbox: {
    iconStyle: {
      borderColor: "#999",
    },
    emphasis: {
      iconStyle: {
        borderColor: "#666",
      },
    },
  },
  legend: {
    textStyle: {
      color: "#555",
    },
  },
  tooltip: {
    axisPointer: {
      lineStyle: {
        color: "#555",
        width: "1",
      },
      crossStyle: {
        color: "#555",
        width: "1",
      },
    },
  },
  timeline: {
    lineStyle: {
      color: "#555",
      width: 1,
    },
    itemStyle: {
      color: "#dd6b66",
      borderWidth: 1,
    },
    controlStyle: {
      color: "#555",
      borderColor: "#555",
      borderWidth: 0.5,
    },
    checkpointStyle: {
      color: "#e43c59",
      borderColor: "#c23531",
    },
    label: {
      color: "#555",
    },
    emphasis: {
      itemStyle: {
        color: "#a9334c",
      },
      controlStyle: {
        color: "#555",
        borderColor: "#555",
        borderWidth: 0.5,
      },
      label: {
        color: "#555",
      },
    },
  },
  visualMap: {
    color: ["#bf444c", "#d88273", "#f6efa6"],
  },
  dataZoom: {
    backgroundColor: "rgba(47,69,84,0)",
    dataBackgroundColor: "rgba(255,255,255,0.3)",
    fillerColor: "rgba(167,183,204,0.4)",
    handleColor: "#a7b7cc",
    handleSize: "100%",
    textStyle: {
      color: "#555",
    },
  },
  markPoint: {
    label: {
      color: "#eee",
    },
    emphasis: {
      label: {
        color: "#eee",
      },
    },
  },
};

export const useSetupEcharts = () => {
  useEffect(() => {
    registerTheme("lepton-light", lightTheme);
    registerTheme("lepton-dark", darkTheme);
  }, []);
};
