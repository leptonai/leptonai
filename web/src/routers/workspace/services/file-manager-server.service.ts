import { Injectable } from "injection-js";
import { FileManagerService } from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { map, Observable } from "rxjs";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";

@Injectable()
export class FileManagerServerService implements FileManagerService<FileInfo> {
  private storage = "default";

  constructor(private apiService: ApiService) {}

  getStoragePath(path?: string) {
    const normalizedPath = path?.replace(/^\//, "");
    return `${this.storage}${path ? `/${normalizedPath}/` : "/"}`;
  }

  list(file?: FileInfo): Observable<FileInfo[]> {
    return this.apiService
      .listStorageEntries(this.getStoragePath(file?.path))
      .pipe(
        map((entries) =>
          entries.map((entry) => ({
            ...entry,
            // FIXME(hsuanxyz): don't hardcode this, should remove it by backend or config from API
            path: entry.path.replace("/mnt/efs/default", ""),
          }))
        )
      );
  }

  create(file: FileInfo, content?: File): Observable<void> {
    if (content) {
      return this.apiService.uploadStorageFile(
        this.getStoragePath(encodeURIComponent(file.path)),
        content
      );
    } else {
      return this.apiService.makeStorageDirectory(
        this.getStoragePath(encodeURIComponent(file.path))
      );
    }
  }

  remove(file: FileInfo): Observable<void> {
    return this.apiService.removeStorageEntry(
      encodeURIComponent(this.getStoragePath(file.path))
    );
  }
}
