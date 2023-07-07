import { Injectable, InjectionToken, Injector } from "injection-js";
import { map, Observable } from "rxjs";
import axios, { AxiosRequestConfig, AxiosResponse } from "axios";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

export const HTTPInterceptorToken = new InjectionToken<HTTPInterceptor>(
  "HTTPInterceptor"
);

export type HTTPRequest<T = SafeAny> = AxiosRequestConfig<T> & {
  context?: HttpContext;
};

export type HTTPResponse<T = SafeAny, D = SafeAny> = AxiosResponse<T, D>;

export abstract class HttpHandler {
  abstract handle<R, D>(req: HTTPRequest<D>): Observable<HTTPResponse<R, D>>;
}

export interface HTTPInterceptor {
  intercept(
    req: AxiosRequestConfig,
    next: HttpHandler
  ): Observable<AxiosResponse>;
}

export class HttpContextToken<T> {
  constructor(public readonly defaultValue: () => T) {}
}

export class HttpContext {
  private readonly map = new Map<HttpContextToken<unknown>, unknown>();

  get<T>(token: HttpContextToken<T>): T {
    if (!this.map.has(token)) {
      this.map.set(token, token.defaultValue());
    }
    return this.map.get(token) as T;
  }

  set<T>(token: HttpContextToken<T>, value: T): HttpContext {
    this.map.set(token, value);
    return this;
  }

  delete(token: HttpContextToken<unknown>): HttpContext {
    this.map.delete(token);
    return this;
  }

  has(token: HttpContextToken<unknown>): boolean {
    return this.map.has(token);
  }

  keys(): IterableIterator<HttpContextToken<unknown>> {
    return this.map.keys();
  }
}

@Injectable()
export class AxiosHandler implements HttpHandler {
  handle(req: HTTPRequest): Observable<HTTPResponse> {
    return new Observable<HTTPResponse>((observer) => {
      const abort = new AbortController();
      const { context: _, ...reqWithoutContext } = req;
      axios
        .request({ ...reqWithoutContext, signal: abort.signal })
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
  handle(req: HTTPRequest): Observable<HTTPResponse> {
    const interceptor = this.injector.get(HTTPInterceptorToken, null);

    // TODO(hsuanxyz): support multiple interceptors and chain them together
    if (interceptor) {
      return interceptor.intercept(req, this.httpHandler);
    }

    return this.httpHandler.handle(req);
  }

  request<T>(req: HTTPRequest): Observable<T> {
    return this.handle(req).pipe(map((r) => r.data));
  }

  put<T>(url: string, data?: SafeAny, config?: HTTPRequest): Observable<T> {
    return this.request({
      method: "PUT",
      url,
      data,
      ...config,
    });
  }

  post<T>(url: string, data?: SafeAny, config?: HTTPRequest): Observable<T> {
    return this.request({
      method: "POST",
      url,
      data,
      ...config,
    });
  }
  get<T>(url: string, config?: HTTPRequest): Observable<T> {
    return this.request({
      method: "GET",
      url,
      ...config,
    });
  }

  delete<T>(url: string, config?: HTTPRequest): Observable<T> {
    return this.request({
      method: "DELETE",
      url,
      ...config,
    });
  }

  patch<T>(url: string, data?: SafeAny, config?: HTTPRequest): Observable<T> {
    return this.request({
      method: "PATCH",
      url,
      data,
      ...config,
    });
  }
}
