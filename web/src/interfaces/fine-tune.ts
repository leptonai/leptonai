export enum FineTuneJobStatus {
  Pending = "P",
  RUNNING = "R",
  CANCELLED = "C",
  SUCCESS = "S",
  FAILED = "F",
}

export interface FineTuneJob {
  id: number;
  created_at: string;
  modified_at: string;
  status: FineTuneJobStatus;
}
