export interface WorkspaceDetail {
  build_time: string;
  git_commit: string;
  resource_quota: {
    limit: { memory: number; accelerator_num: number; cpu: number };
    used: { memory: number; accelerator_num: number; cpu: number };
  };
}

export interface AuthorizedWorkspace {
  url: string;
  id: string;
  token: string;
  status: string;
  paymentMethodAttached: boolean;
  displayName: string;
}

export interface Workspace {
  auth: AuthorizedWorkspace;
  isBillingSupported: boolean;
  isPastDue: boolean;
}
