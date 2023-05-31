import { Injectable } from "injection-js";
import prettyBytes from "pretty-bytes";
const formatMap = {
  qps: (v: number) => `${v !== null ? v.toFixed(4) : "-"}`,
  latency: (v: number) => `${v !== null ? `${(v * 1000).toFixed(0)}ms` : "-"}`,
  util: (v: number) => `${(v * 100).toFixed(1)}%`,
  memory: (v: number) => prettyBytes(v),
};
const tipsMap = {
  qps: `QPS stands for Queries Per Second. It is a metric used to measure the rate at which queries or requests are processed by a system. QPS indicates how many queries a system can handle within a one-second time frame.`,
  latency: `Latency refers to the time delay between the initiation of a request or task and the receipt of a response or completion of that task. It is a measure of the time taken for data to travel from the source to the destination, usually measured in milliseconds (ms).`,
  memory: `Memory usage refers to the amount of computer memory being utilized at a given time. It is a measure of how much memory is actively being used to store data and instructions by running applications and the operating system.`,
  cpu: `CPU usage refers to the amount of processing power or capacity that a central processing unit (CPU) is currently utilizing to perform tasks and execute instructions.`,
  gpu: `GPU usage refers to the utilization or workload of a graphics processing unit (GPU) in a computer system to perform tasks and execute instructions.`,
  gpu_memory: `GPU memory usage refers to the amount of memory that a graphics processing unit (GPU) is currently utilizing to store data and perform computations.`,
};
@Injectable()
export class MetricUtilService {
  static getMetricFormat(
    metric: keyof typeof formatMap
  ): (v: number) => string {
    return formatMap[metric];
  }
  static getMetricTips(metric: keyof typeof tipsMap): string {
    return tipsMap[metric];
  }
}
