import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Injectable } from "injection-js";
import { Observable } from "rxjs";

@Injectable()
export class BillingService {
  getPortal(): Observable<{ url: string }> {
    return this.apiService.getPortal();
  }

  getInvoice() {
    return this.apiService.getInvoice();
  }

  constructor(private apiService: ApiService) {}
}
