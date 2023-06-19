import { Injectable, InjectionToken, Injector } from "injection-js";
import { map, Observable } from "rxjs";
import axios, { AxiosRequestConfig, AxiosResponse } from "axios";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

export const HTTPInterceptorToken = new InjectionToken<HTTPInterceptor>(
  "HTTPInterceptor"
);

export type Request<T = SafeAny> = AxiosRequestConfig<T>;
export type Response<T = SafeAny, D = SafeAny> = AxiosResponse<T, D>;

export abstract class HttpHandler {
  abstract handle<R, D>(req: Request<D>): Observable<Response<R, D>>;
}

export interface HTTPInterceptor {
  intercept(
    req: AxiosRequestConfig,
    next: HttpHandler
  ): Observable<AxiosResponse>;
}

@Injectable()
export class AxiosHandler implements HttpHandler {
  handle(req: AxiosRequestConfig): Observable<AxiosResponse> {
    return new Observable<AxiosResponse>((observer) => {
      const abort = new AbortController();
      axios
        .request({ ...req, signal: abort.signal })
        .then((r) => {
          observer.next(r);
          observer.complete();
        })
        .catch((e) => observer.error(e));
      return () => abort.abort();
    });
  }
}

@Injectable()
export class HttpClientService {
  constructor(private injector: Injector, private httpHandler: AxiosHandler) {}
  handle(req: AxiosRequestConfig): Observable<AxiosResponse> {
    const interceptor = this.injector.get(HTTPInterceptorToken, null);

    // TODO(hsuanxyz): support multiple interceptors and chain them together
    if (interceptor) {
      return interceptor.intercept(req, this.httpHandler);
    }

    return this.httpHandler.handle(req);
  }

  request<T>(req: AxiosRequestConfig): Observable<T> {
    return this.handle(req).pipe(map((r) => r.data));
  }

  put<T>(...args: Parameters<typeof axios.put>): Observable<T> {
    return this.request({
      method: "PUT",
      url: args[0],
      data: args[1],
      ...args[2],
    });
  }

  post<T>(...args: Parameters<typeof axios.post>): Observable<T> {
    return this.request({
      method: "POST",
      url: args[0],
      data: args[1],
      ...args[2],
    });
  }
  get<T>(...args: Parameters<typeof axios.get>): Observable<T> {
    return this.request({
      method: "GET",
      url: args[0],
      ...args[1],
    });
  }

  delete<T>(...args: Parameters<typeof axios.delete>): Observable<T> {
    return this.request({
      method: "DELETE",
      url: args[0],
      ...args[1],
    });
  }

  patch<T>(...args: Parameters<typeof axios.patch>): Observable<T> {
    return this.request({
      method: "PATCH",
      url: args[0],
      data: args[1],
      ...args[2],
    });
  }
}
