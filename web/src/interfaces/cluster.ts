export interface ClusterDetail {
  cluster_name: string;
  supported_accelerators: { [key: string]: number };
  max_generic_compute_size: { Memory: number; Core: number };
}

export interface AuthorizedCluster {
  url: string;
  token: string;
}

export interface Cluster {
  auth: AuthorizedCluster;
  data: ClusterDetail;
}
