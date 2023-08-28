import { Injectable } from "injection-js";

import { map, Observable, shareReplay } from "rxjs";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";

interface PlaygroundConfig {
  [key: string]: {
    name: string;
    description: string;
    api: string;
  };
}

@Injectable()
export class PlaygroundService {
  private config$?: Observable<PlaygroundConfig>;

  constructor(private http: HttpClientService) {}

  getPlaygroundConfig(): Observable<PlaygroundConfig> {
    if (!this.config$) {
      this.config$ = this.http
        .get<PlaygroundConfig>(
          `https://oauth.lepton.ai/storage/v1/object/sign/config/playground.json?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmwiOiJjb25maWcvcGxheWdyb3VuZC5qc29uIiwiaWF0IjoxNjkyNDY5NDA1LCJleHAiOjE3MjQwMDU0MDV9.wjU1mnmtt127kQlk02dvfybom6u1QzFCT7Ixvk6ypBs&t=${Date.now()}`
        )
        .pipe(shareReplay(1));
    }
    return this.config$;
  }

  getStableDiffusionXlBackend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["stable-diffusion-xl"].api)
    );
  }

  getLlamaBackend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["llama2"].api)
    );
  }

  getLlama70bBackend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["llama2-70b"].api)
    );
  }
}
