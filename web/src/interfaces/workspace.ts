export interface WorkspaceDetail {
  build_time: string;
  git_commit: string;
}

export interface AuthorizedWorkspace {
  url: string;
  id: string;
  token: string;
  status: string;
  displayName: string;
}

export interface Workspace {
  auth: AuthorizedWorkspace;
  data: WorkspaceDetail | null;
  isBillingSupported: boolean;
  isPastDue: boolean;
}
