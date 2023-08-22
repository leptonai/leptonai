export enum State {
  Running = "Running",
  NotReady = "Not Ready",
  Starting = "Starting",
  Updating = "Updating",
  Unknown = "",
}

type Token =
  | { value_from: { token_name_ref: "WORKSPACE_TOKEN" } }
  | { value: string };

export interface Deployment {
  name: string;
  photon_id: string;
  created_at: number;
  status: {
    endpoint: { external_endpoint: string };
    state: State | string;
  };
  resource_requirement: {
    resource_shape?: string;
    min_replicas: number;
  };
  envs?: Array<DeploymentEnv | DeploymentSecretEnv>;
  mounts?: Array<DeploymentMount>;
  api_tokens?: Token[];
  pull_image_secrets?: string[];
}

export interface DeploymentMount {
  mount_path: string;
  path: string;
}

export interface DeploymentEnv {
  name: string;
  value: string;
}

export interface DeploymentSecretEnv {
  name: string;
  value_from: { secret_name_ref: string };
}

export interface Replica {
  id: string;
}

export interface Metric {
  metric: { name: string; handler?: string };
  values: Array<[number, string]>;
}

/**
 * https://pkg.go.dev/k8s.io/api/events/v1#Event
 */
export enum DeploymentEventTypes {
  Normal = "Normal",
  Warning = "Warning",
}
export interface DeploymentEvent {
  type: string;
  reason: DeploymentEventTypes | string;
  count: number;
  last_observed_time: string;
}

export enum ReadinessReason {
  ReadinessReasonReady = "Ready",
  ReadinessReasonInProgress = "InProgress",
  ReadinessReasonNoCapacity = "NoCapacity",
  ReadinessReasonUserCodeError = "UserCodeError",
  ReadinessReasonDeploymentConfigError = "DeploymentConfigError",
  ReadinessReasonSystemError = "SystemError",
  ReadinessReasonUnknown = "Unknown",
}

export interface DeploymentReadinessItem {
  reason: ReadinessReason;
  message: string;
}

export interface DeploymentReadiness {
  [replicaID: string]: DeploymentReadinessItem[];
}

export interface ReplicaTermination {
  started_at: number;
  finished_at: number;
  exit_code: number;
  reason: string;
  message: string;
}

export interface DeploymentTerminations {
  [replicaID: string]: ReplicaTermination[];
}
