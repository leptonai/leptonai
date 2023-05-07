import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import { GroupedModel, Model } from "@lepton-dashboard/interfaces/model.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";

@Injectable()
export class ModelService {
  private list$ = new BehaviorSubject<Model[]>([]);
  list(): Observable<Model[]> {
    return this.list$;
  }

  groups(): Observable<GroupedModel[]> {
    return this.list().pipe(
      map((models) => {
        const groupModels: GroupedModel[] = [];
        models.forEach((model) => {
          const target = groupModels.find((g) => g.name === model.name);
          if (target) {
            target.data.push(model);
            if (!target.latest || target.latest.created_at < model.created_at) {
              target.latest = model;
            }
          } else {
            groupModels.push({
              name: model.name,
              data: [model],
              latest: model,
            });
          }
        });
        return groupModels;
      })
    );
  }

  groupId(name: string): Observable<GroupedModel | undefined> {
    return this.groups().pipe(
      map((list) => list.find((item) => item.name === name))
    );
  }

  id(id: string): Observable<Model | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }

  delete(id: string): Observable<void> {
    return this.apiService.deleteModel(id);
  }

  refresh() {
    return this.apiService.listModels().pipe(
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((l) => this.list$.next(l))
    );
  }
  constructor(private apiService: ApiService) {}
}
