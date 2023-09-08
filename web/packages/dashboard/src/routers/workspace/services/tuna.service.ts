import { State } from "@lepton-dashboard/interfaces/deployment";
import { Injectable } from "injection-js";
import { forkJoin, map, mergeMap, Observable } from "rxjs";
import {
  FineTuneJob,
  FineTuneJobStatus,
  TunaInference,
} from "@lepton-dashboard/interfaces/fine-tune";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";

@Injectable()
export class TunaService {
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

  addJob(name: string, file: File): Observable<FineTuneJob> {
    return this.apiService.addFineTuneJob(name, file);
  }

  cancelJob(id: number): Observable<void> {
    return this.apiService.cancelFineTuneJob(id);
  }

  getJob(id: number): Observable<FineTuneJob> {
    return this.apiService.getFineTuneJob(id);
  }

  createInference(name: string, outputDir: string): Observable<void> {
    return this.apiService.createInference({
      metadata: {
        name,
      },
      spec: {
        tuna_output_dir: outputDir.replace(/^gs:\/\/tuna-dish/, "/tuna"),
      },
    });
  }

  deleteInference(name: string): Observable<void> {
    return this.apiService.deleteInference(name);
  }

  getInference(name: string): Observable<TunaInference | null> {
    return this.apiService.getInference(name);
  }

  listAvailableInferences(): Observable<TunaInference[]> {
    return this.listJobs(FineTuneJobStatus.SUCCESS).pipe(
      mergeMap((jobs) => {
        const observables = jobs.map((job) => this.getInference(job.name));
        return forkJoin(observables);
      }),
      map((inferences) => [
        ...inferences.filter(
          (inference): inference is TunaInference =>
            inference !== null && inference?.status?.state === State.Running
        ),
      ])
    );
  }
}
