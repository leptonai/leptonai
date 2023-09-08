import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Injectable } from "injection-js";

@Injectable()
export class WorkspaceService {
  getWorkspaceDetail() {
    return this.apiService.getWorkspaceDetail();
  }
  constructor(private apiService: ApiService) {}
}
