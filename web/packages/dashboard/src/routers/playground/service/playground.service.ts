import { Injectable } from "injection-js";

import { map, mergeMap, Observable, shareReplay } from "rxjs";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";
import pathJoin from "@lepton-libs/url/path-join";

interface PlaygroundConfig {
  [key: string]: {
    name: string;
    description: string;
    api: string;
  };
}

interface ModeItem {
  id: string;
  object: string;
  created: number;
  owned_by: string;
  root: string;
  parent: null;
  permission: Record<string, unknown>[];
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

  listCodeLlamaModels(): Observable<string[]> {
    return this.getCodeLlamaBackend().pipe(
      mergeMap((backend) => {
        return this.http.get<{
          data: ModeItem[];
          object: "list";
        }>(pathJoin(backend, "models"));
      }),
      map((modes) =>
        modes.data
          .map((mode) => mode.id)
          // ignore models that are compatible with the OpenAI API
          .filter(
            (id) =>
              ![
                "gpt-3.5-turbo",
                "text-davinci-003",
                "text-embedding-ada-002",
              ].includes(id)
          )
      )
    );
  }

  getCodeLlamaBackend(): Observable<string> {
    return this.getPlaygroundConfig().pipe(
      map((config) => config["codellama"].api)
    );
  }
}
