import { Injectable } from "injection-js";
import { map, Observable, of } from "rxjs";
import { GroupedModel, Model } from "@lepton-dashboard/interfaces/model.ts";

@Injectable()
export class ModelService {
  list(): Observable<Model[]> {
    return of([
      {
        id: "photon-1",
        name: "example-photon-1",
        model_source: "hf:example/1.0.0",
        requirement_dependency: [
          "numpy==1.19.3",
          "torch==1.10.0",
          "transformers==4.15.0",
        ],
        image_url: "docker.io/library/python:3.9.6-slim-buster",
        entrypoint: "python main.py",
        exposed_ports: [8000],
        created_at: 1651497985000,
      },
      {
        id: "photon-2",
        name: "example-photon-2",
        model_source: "hf:example/1.1.0",
        image_url: "docker.io/library/python:3.9.6-slim-buster",
        entrypoint: "python main.py",
        exposed_ports: [8080],
        container_args: ["--shm-size=2g"],
        created_at: 1651608499000,
      },
      {
        id: "photon-3",
        name: "example-photon-3",
        model_source: "hf:example/2.0.0",
        requirement_dependency: ["tensorflow==2.6.0", "keras==2.6.0"],
        image_url: "docker.io/library/tensorflow:2.6.0",
        exposed_ports: [5000],
        container_args: ["--gpus=all", "--env", "CUDA_VISIBLE_DEVICES=0"],
        created_at: 1651862976000,
      },
      {
        id: "photon-4",
        name: "example-photon-3",
        model_source: "hf:example/2.1.0",
        requirement_dependency: ["tensorflow==2.7.0", "keras==2.7.0"],
        image_url: "docker.io/library/tensorflow:2.7.0",
        entrypoint: "python main.py",
        exposed_ports: [5000],
        container_args: ["--gpus=all", "--env", "CUDA_VISIBLE_DEVICES=0"],
        created_at: 1651926176000,
      },
    ]).pipe(map((item) => item.sort((a, b) => b.created_at - a.created_at)));
  }

  listGroup(): Observable<GroupedModel[]> {
    return this.list().pipe(
      map((models) => {
        const groupModels: GroupedModel[] = [];
        models.forEach((model) => {
          const target = groupModels.find((g) => g.name === model.name);
          if (target) {
            target.data.push(model);
            if (!target.latest || target.latest.created_at < model.created_at) {
              target.latest = model;
            }
          } else {
            groupModels.push({
              name: model.name,
              data: [model],
              latest: model,
            });
          }
        });
        return groupModels;
      })
    );
  }

  getGroup(name: string): Observable<GroupedModel | undefined> {
    return this.listGroup().pipe(
      map((list) => list.find((item) => item.name === name))
    );
  }
  getById(id: string): Observable<Model | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }
}
