export interface Deployment {
  id: string;
  name: string;
  photon_id: string;
  status: {
    endpoint: { internal_endpoint: string; external_endpoint: string };
    state: string;
  };
  resource_requirement: {
    memory: number;
    accelerator_type?: string;
    accelerator_num?: number;
    min_replica: number;
    cpu: number;
  };
}
