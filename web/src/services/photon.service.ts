import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import { Photon, PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { ApiService } from "@lepton-dashboard/services/api.service";

@Injectable()
export class PhotonService {
  private list$ = new BehaviorSubject<Photon[]>([]);

  listGroups(): Observable<PhotonGroup[]> {
    return this.list().pipe(
      map((photons) => {
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
        return photonGroups;
      })
    );
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
