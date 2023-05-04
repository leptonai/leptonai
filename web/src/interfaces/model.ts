export interface Model {
  id: string;
  name: string;
  model_source: string;
  image_url: string;
  created_at: number;
  exposed_ports?: number[];
  requirement_dependency?: string[];
  container_args?: string[];
  entrypoint?: string;
}

export interface GroupedModel {
  name: string;
  data: Model[];
  latest: Model;
}
