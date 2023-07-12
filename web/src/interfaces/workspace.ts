export interface WorkspaceDetail {
  workspace_name: string;
  build_time: string;
  git_commit: string;
}

export interface AuthorizedWorkspace {
  url: string;
  token: string;
}

export interface Workspace {
  auth: AuthorizedWorkspace;
  data: WorkspaceDetail;
}
