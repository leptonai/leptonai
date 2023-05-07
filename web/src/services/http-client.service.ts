import { Injectable } from "injection-js";
import { map, Observable } from "rxjs";
import { fromPromise } from "rxjs/internal/observable/innerFrom";
import axios from "axios";

@Injectable()
export class HttpClientService {
  post<T>(url: string, body: unknown): Observable<T> {
    return fromPromise(axios.post(url, body)).pipe(map((r) => r.data));
  }
  get<T>(url: string): Observable<T> {
    return fromPromise(axios.get(url)).pipe(map((d) => d.data));
  }

  delete<T>(url: string): Observable<T> {
    return fromPromise(axios.delete(url)).pipe(map((d) => d.data));
  }

  patch<T>(url: string, body: unknown): Observable<T> {
    return fromPromise(axios.patch(url, body)).pipe(map((r) => r.data));
  }
}
