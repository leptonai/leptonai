import { Injectable } from "injection-js";

const StorageKeys = {
  DEPLOYMENT_TIME: "lepton-deployment-latest-date",
  PHOTON_TIME: "lepton-photon-latest-date",
  PHOTON_LAYOUT: "lepton-photon-layout",
};

type Key = keyof typeof StorageKeys;

@Injectable()
export class StorageService {
  set(key: Key, value: string) {
    localStorage.setItem(StorageKeys[key], value);
  }

  get(key: Key): string | null {
    return localStorage.getItem(StorageKeys[key]);
  }
}
