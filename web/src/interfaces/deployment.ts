export interface Deployment {
  id: string;
  name: string;
  photon_id: string;
  created_at: number;
  status: {
    endpoint: { internal_endpoint: string; external_endpoint: string };
    state: string;
  };
  resource_requirement: {
    memory: number;
    cpu: number;
    min_replicas: number;
    accelerator_type?: string;
    accelerator_num?: number;
  };
  envs?: { name: string; value: string }[];
}

export interface Instance {
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
