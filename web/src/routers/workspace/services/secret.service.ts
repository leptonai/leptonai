import { Secret } from "@lepton-dashboard/interfaces/secret";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Injectable } from "injection-js";
import { map, Observable } from "rxjs";

@Injectable()
export class SecretService {
  createOrUpdateSecret(secret: Secret): Observable<void> {
    return this.apiService.createSecret(secret);
  }

  listSecrets(): Observable<Secret[]> {
    return this.apiService
      .listSecrets()
      .pipe(
        map((secrets) =>
          secrets
            .map((secret) => ({ name: secret, value: "" }))
            .sort((a, b) => a.name.localeCompare(b.name))
        )
      );
  }

  deleteSecret(id: string): Observable<void> {
    return this.apiService.deleteSecret(id);
  }

  constructor(private apiService: ApiService) {}
}
