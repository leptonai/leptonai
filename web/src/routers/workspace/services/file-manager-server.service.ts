import { Injectable } from "injection-js";
import { FileManagerService } from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { map, Observable } from "rxjs";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";

@Injectable()
export class FileManagerServerService implements FileManagerService<FileInfo> {
  private storage = "default";

  constructor(private apiService: ApiService) {}

  getStoragePath(file?: FileInfo) {
    const normalizedPath = file?.path.replace(/^\//, "") || "";
    const path = normalizedPath ? encodeURIComponent(normalizedPath) : "";
    // we don't need to encode the end slash
    return `${this.storage}${
      path ? `/${path}` + (file?.type === "dir" ? "/" : "") : "/"
    }`;
  }

  list(file?: FileInfo): Observable<FileInfo[]> {
    return this.apiService.listStorageEntries(this.getStoragePath(file)).pipe(
      map((entries) =>
        entries
          .map((entry) => ({
            ...entry,
            // FIXME(hsuanxyz): don't hardcode this, should remove it by backend or config from API
            path: entry.path.replace("/mnt/efs/default", ""),
          }))
          .sort((a, b) => {
            if (a.type === b.type) {
              return a.name.localeCompare(b.name);
            } else {
              return a.type === "dir" ? -1 : 1;
            }
          })
      )
    );
  }

  create(file: FileInfo, content?: File): Observable<void> {
    if (content) {
      return this.apiService.uploadStorageFile(
        this.getStoragePath(file),
        content
      );
    } else {
      return this.apiService.makeStorageDirectory(this.getStoragePath(file));
    }
  }

  remove(file: FileInfo): Observable<void> {
    return this.apiService.removeStorageEntry(this.getStoragePath(file));
  }
}
