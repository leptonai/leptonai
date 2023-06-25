import { Injectable } from "injection-js";
import { map, Observable } from "rxjs";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";

@Injectable()
export class FineTuneService {
  constructor(private apiService: ApiService) {}

  listJobs(status?: FineTuneJobStatus): Observable<FineTuneJob[]> {
    return this.apiService.listFineTuneJobs(status).pipe(
      map((jobs) =>
        jobs.sort((a, b) => {
          const aTime = new Date(a.created_at).getTime();
          const bTime = new Date(b.created_at).getTime();
          return bTime - aTime;
        })
      )
    );
  }

  addJob(file: File): Observable<FineTuneJob> {
    return this.apiService.addFineTuneJob(file);
  }

  cancelJob(id: number): Observable<void> {
    return this.apiService.cancelFineTuneJob(id);
  }

  getJob(id: number): Observable<FineTuneJob> {
    return this.apiService.getFineTuneJob(id);
  }
}
