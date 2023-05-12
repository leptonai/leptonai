export interface Photon {
  id: string;
  name: string;
  model: string;
  image: string;
  created_at: number;
  exposed_ports?: number[];
  requirement_dependency?: string[];
  container_args?: string[];
  entrypoint?: string;
}

export interface PhotonGroup extends Photon {
  versions: Array<{ id: string; created_at: number }>;
}
