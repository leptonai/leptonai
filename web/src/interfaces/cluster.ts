export interface Cluster {
  cluster_name: string;
  supported_accelerators: { [key: string]: number };
  max_generic_compute_size: { Memory: number; Core: number };
}
