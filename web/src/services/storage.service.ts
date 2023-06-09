import { Injectable } from "injection-js";

const StorageKeys = {
  DEPLOYMENT_TIME: "lepton-deployment-latest-date",
  PHOTON_TIME: "lepton-photon-latest-date",
  PHOTON_LAYOUT: "lepton-photon-layout",
  THEME: "lepton-theme",
};

type Key = keyof typeof StorageKeys;

@Injectable()
export class StorageService {
  static GLOBAL_SCOPE = "lepton-global";
  set(scope: string, key: Key, value: string) {
    localStorage.setItem(`${scope}-${StorageKeys[key]}`, value);
  }

  get(scope: string, key: Key): string | null {
    return localStorage.getItem(`${scope}-${StorageKeys[key]}`);
  }
}
