export interface WorkspaceDetail {
  // TODO(hsuanxyz): need to change to workspace_name
  cluster_name: string;
  build_time: string;
  git_commit: string;
  supported_accelerators: { [key: string]: number };
  max_generic_compute_size: { memory: number; core: number };
}

export interface AuthorizedWorkspace {
  url: string;
  token: string;
}

export interface Workspace {
  auth: AuthorizedWorkspace;
  data: WorkspaceDetail;
}
