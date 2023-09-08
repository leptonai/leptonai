export enum FineTuneJobStatus {
  PENDING = "P",
  RUNNING = "R",
  CANCELLED = "C",
  SUCCESS = "S",
  FAILED = "F",
}

export interface FineTuneJob {
  id: number;
  name: string;
  created_at: string;
  modified_at: string;
  output_dir: string;
  status: FineTuneJobStatus;
}

export interface TunaInferenceSpec {
  tuna_output_dir: string;
  photon_id?: string;
}

export interface TunaInferenceMetadata {
  name: string;
}

export interface TunaInferenceStatus {
  chat_endpoint: string;
  api_endpoint: string;
  state: string;
}

export interface TunaInference {
  metadata: TunaInferenceMetadata;
  spec: TunaInferenceSpec;
  status?: TunaInferenceStatus;
}
