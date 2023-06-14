import { Injectable } from "injection-js";
import { map, Observable, of } from "rxjs";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";

@Injectable()
export class FineTuneService {
  private backendUrl = "https://tuna-dev.vercel.app";

  constructor(private httpClientService: HttpClientService) {}

  listJobs(status?: FineTuneJobStatus): Observable<FineTuneJob[]> {
    return this.httpClientService
      .get<FineTuneJob[]>(
        `${this.backendUrl}/job/list${status ? `/${status}` : ""}`
      )
      .pipe(
        map((jobs) =>
          jobs.sort((a, b) => {
            const aTime = new Date(a.created_at).getTime();
            const bTime = new Date(b.created_at).getTime();
            return bTime - aTime;
          })
        )
      );
  }

  creatJob(file: File): Observable<void> {
    const formData = new FormData();
    formData.append("data", file);
    return this.httpClientService.post(`${this.backendUrl}/job/add`, formData);
  }

  cancelJob(id: number): Observable<void> {
    return this.httpClientService.get(`${this.backendUrl}/job/cancel/${id}`);
  }

  getJob(_id: number): Observable<FineTuneJob> {
    return of(null! as FineTuneJob);
  }
}
