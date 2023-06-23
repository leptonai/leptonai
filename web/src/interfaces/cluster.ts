export interface ClusterDetail {
  cluster_name: string;
  build_time: string;
  git_commit: string;
  supported_accelerators: { [key: string]: number };
  max_generic_compute_size: { memory: number; core: number };
}

export interface AuthorizedCluster {
  url: string;
  token: string;
}

export interface Cluster {
  auth: AuthorizedCluster;
  data: ClusterDetail;
}
