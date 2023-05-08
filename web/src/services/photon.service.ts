import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import { GroupedPhoton, Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";

@Injectable()
export class PhotonService {
  private list$ = new BehaviorSubject<Photon[]>([]);
  list(): Observable<Photon[]> {
    return this.list$;
  }

  groups(): Observable<GroupedPhoton[]> {
    return this.list().pipe(
      map((photons) => {
        const groupPhotons: GroupedPhoton[] = [];
        photons.forEach((photon) => {
          const target = groupPhotons.find((g) => g.name === photon.name);
          if (target) {
            target.data.push(photon);
            if (
              !target.latest ||
              target.latest.created_at < photon.created_at
            ) {
              target.latest = photon;
            }
          } else {
            groupPhotons.push({
              name: photon.name,
              data: [photon],
              latest: photon,
            });
          }
        });
        return groupPhotons;
      })
    );
  }

  groupId(name: string): Observable<GroupedPhoton | undefined> {
    return this.groups().pipe(
      map((list) => list.find((item) => item.name === name))
    );
  }

  id(id: string): Observable<Photon | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }

  delete(id: string): Observable<void> {
    return this.apiService.deletePhoton(id);
  }

  create(body: FormData): Observable<void> {
    return this.apiService.createPhoton(body);
  }

  refresh() {
    return this.apiService.listPhotons().pipe(
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((l) => this.list$.next(l))
    );
  }
  constructor(private apiService: ApiService) {}
}
