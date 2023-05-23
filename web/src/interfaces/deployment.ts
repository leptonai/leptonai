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
}

export interface Instance {
  id: string;
}
