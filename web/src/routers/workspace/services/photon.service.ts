import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import { Photon, PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { retryBackoff } from "@lepton-libs/rxjs/retry-backoff";

@Injectable()
export class PhotonService {
  private list$ = new BehaviorSubject<Photon[]>([]);
  private listGroup$ = new BehaviorSubject<PhotonGroup[]>([]);

  listGroups(): Observable<PhotonGroup[]> {
    return this.listGroup$;
  }
  list(): Observable<Photon[]> {
    return this.list$;
  }

  listByName(name: string): Observable<Photon[]> {
    return this.list().pipe(
      map((list) => list.filter((item) => item.name === name))
    );
  }

  id(id: string): Observable<Photon | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }

  getDownloadUrlById(id: string) {
    return this.apiService.getPhotonDownloadUrl(id);
  }

  delete(id: string): Observable<void> {
    return this.apiService.deletePhoton(id).pipe(
      tap(() => {
        const list = this.list$.value;
        const index = list.findIndex((item) => item.id === id);
        if (index !== -1) {
          list.splice(index, 1);
          this.list$.next(list);
        }
      })
    );
  }

  create(body: FormData): Observable<void> {
    return this.apiService.createPhoton(body);
  }

  refresh() {
    return this.apiService.listPhotons().pipe(
      retryBackoff({
        count: 5,
        delay: 1000,
      }),
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((photons) => {
        this.list$.next(photons);
        const photonGroups: PhotonGroup[] = [];
        photons.forEach((photon) => {
          const target = photonGroups.find((g) => g.name === photon.name);
          if (target) {
            target.versions.push({
              id: photon.id,
              created_at: photon.created_at,
            });
          } else {
            photonGroups.push({
              ...photon,
              versions: [
                {
                  id: photon.id,
                  created_at: photon.created_at,
                },
              ],
            });
          }
        });
        this.listGroup$.next(photonGroups);
      })
    );
  }
  constructor(private apiService: ApiService) {}
}
