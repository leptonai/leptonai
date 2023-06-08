import { Injectable } from "injection-js";
import { map, Observable } from "rxjs";
import { fromPromise } from "rxjs/internal/observable/innerFrom";
import axios from "axios";

@Injectable()
export class HttpClientService {
  post<T>(...args: Parameters<typeof axios.post>): Observable<T> {
    return fromPromise(axios.post(...args)).pipe(map((r) => r.data));
  }
  get<T>(...args: Parameters<typeof axios.get>): Observable<T> {
    return fromPromise(axios.get(...args)).pipe(map((d) => d.data));
  }

  delete<T>(...args: Parameters<typeof axios.delete>): Observable<T> {
    return fromPromise(axios.delete(...args)).pipe(map((d) => d.data));
  }

  patch<T>(...args: Parameters<typeof axios.patch>): Observable<T> {
    return fromPromise(axios.patch(...args)).pipe(map((r) => r.data));
  }

  put<T>(...args: Parameters<typeof axios.put>): Observable<T> {
    return fromPromise(axios.put(...args)).pipe(map((r) => r.data));
  }

  request<T>(...args: Parameters<typeof axios.request>): Observable<T> {
    return fromPromise(axios.request(...args)).pipe(map((r) => r.data));
  }
}
