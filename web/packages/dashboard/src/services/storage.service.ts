import { Injectable } from "injection-js";

const StorageKeys = {
  DEPLOYMENT_TIME: "lepton-deployment-latest-date",
  PHOTON_TIME: "lepton-photon-latest-date",
  PHOTON_LAYOUT: "lepton-photon-layout",
  THEME: "lepton-theme",
  WORKSPACE_TOKEN: "lepton-workspace-token",
};

type Key = keyof typeof StorageKeys;

@Injectable()
export class StorageService {
  static GLOBAL_SCOPE = "lepton-global";

  storageKey(scope: string, key: Key) {
    return `${scope}-${StorageKeys[key]}`;
  }

  set(scope: string, key: Key, value: string) {
    localStorage.setItem(this.storageKey(scope, key), value);
  }

  get(scope: string, key: Key): string | null {
    return localStorage.getItem(this.storageKey(scope, key));
  }
}
