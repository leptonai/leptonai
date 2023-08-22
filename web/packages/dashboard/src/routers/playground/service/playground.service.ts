import { Injectable } from "injection-js";

import { map, Observable } from "rxjs";
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
  constructor(private http: HttpClientService) {}

  getPlaygroundConfig(): Observable<PlaygroundConfig> {
    return this.http.get<PlaygroundConfig>(
      `https://oauth.lepton.ai/storage/v1/object/sign/config/playground.json?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmwiOiJjb25maWcvcGxheWdyb3VuZC5qc29uIiwiaWF0IjoxNjkyNDY5NDA1LCJleHAiOjE3MjQwMDU0MDV9.wjU1mnmtt127kQlk02dvfybom6u1QzFCT7Ixvk6ypBs&t=${Date.now()}`
    );
  }

  getStableDiffusionXlBackend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["stable-diffusion-xl"].api)
    );
  }

  getLlama2Backend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["llama2"].api)
    );
  }
}
