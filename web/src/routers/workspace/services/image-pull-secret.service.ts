import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Injectable } from "injection-js";
import { ImagePullSecret } from "@lepton-dashboard/interfaces/image-pull-secrets";

@Injectable()
export class ImagePullSecretService {
  constructor(private apiService: ApiService) {}

  listImagePullSecrets() {
    return this.apiService.listImagePullSecrets();
  }

  createImagePullSecret(secret: ImagePullSecret) {
    return this.apiService.createImagePullSecret(secret);
  }

  deleteImagePullSecret(name: string) {
    return this.apiService.deleteImagePullSecret(name);
  }
}
