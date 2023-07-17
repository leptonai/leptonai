import { Injectable } from "injection-js";
import { matchPath } from "react-router-dom";
import type { NavigateOptions, To } from "react-router-dom";
import { Observable, Subject } from "rxjs";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";

type Optional<T, K extends keyof T> = Pick<Partial<T>, K> & Omit<T, K>;

/**
 * Extract all params keys from path string
 * @example
 * type Params = PathParamKeys<'/workspace/:workspaceId?/deployments/list/:photonId?'>
 *   // Params = 'workspaceId' | 'photonId'
 */
type PathParamKeys<Path extends string> = Path extends `${infer L}/${infer R}`
  ? PathParamKeys<L> | PathParamKeys<R>
  : Path extends `:${infer Param}`
  ? Param extends `${infer Optional}?`
    ? Optional
    : Param
  : never;

/**
 * Extract all optional params keys from path string
 * @example
 * type Params = PathParamOptionalKeys<'/workspace/:workspaceId?/deployments/list/:photonId?'>
 *   // Params = 'photonId'
 */
type PathParamOptionalKeys<Path extends string> =
  Path extends `${infer L}/${infer R}`
    ? PathParamOptionalKeys<L> | PathParamOptionalKeys<R>
    : Path extends `:${infer Param}`
    ? Param extends `${infer Optional}?`
      ? Optional
      : never
    : never;

/**
 * conversion all params to string template literal type from path string
 * @example
 * type Path = PathString<'/workspace/:workspaceId?/deployments/list/:photonId?'>
 *   // Path = `/workspace/${string}/deployments/list/${string}`
 */
type AnyPathStringLiteral<Path extends string> =
  Path extends `${infer L}/${infer R}`
    ? `${AnyPathStringLiteral<L>}/${AnyPathStringLiteral<R>}`
    : Path extends `:${string}`
    ? `${string}`
    : Path;

/**
 * Only conversion required params to string template literal type from path string
 * @example
 * type Path = RequiredPathStringLiteral<'/workspace/:workspaceId?/deployments/list/:photonId?'>
 *   // Path = `/workspace/${string}/deployments/list`
 */
type RequiredPathStringLiteral<Path extends string> =
  Path extends `${infer L}/${infer R}`
    ? `${RequiredPathStringLiteral<L>}${RequiredPathStringLiteral<R>}`
    : Path extends `:${infer Param}`
    ? Param extends `${string}?`
      ? ""
      : `/${string}`
    : Path extends ""
    ? ""
    : `/${Path}`;

/**
 * conversion string template literal type from path string
 * @example
 * type Path = PathStringLiteral<'/workspace/:workspaceId?/deployments/list/:photonId?'>
 *   // Path = `/workspace/${string}/deployments/list/${string}` | `/workspace/${string}/deployments/list`
 */
type PathStringLiteral<Path extends string> =
  | AnyPathStringLiteral<Path>
  | RequiredPathStringLiteral<Path>;

export type Routers = typeof RoutersMap;

/**
 * Extract all params with optional from path string
 */
export type PathParams<T extends keyof Routers> = Optional<
  {
    [K in PathParamKeys<Routers[T]>]: string;
  },
  PathParamOptionalKeys<Routers[T]>
>;

export type IsNoParams<T extends keyof Routers> = PathParamKeys<
  Routers[T]
> extends never // if no params
  ? true
  : false;

export type IsOptionalParams<T extends keyof Routers> = PathParamKeys<
  Routers[T]
> extends never // if no params
  ? true
  : { [K in PathParamOptionalKeys<Routers[T]>]?: string } extends PathParams<T> // if all params are optional
  ? true
  : false;

export type NullablePathParams<T extends keyof Routers> = PathParamKeys<
  Routers[T]
> extends never // if no params
  ? null | undefined
  : { [K in PathParamOptionalKeys<Routers[T]>]?: string } extends PathParams<T> // if all params are optional
  ? PathParams<T> | null | undefined
  : PathParams<T>;

type NavigateToOptions = NavigateOptions & {
  query?: string | URLSearchParams;
};

export const RoutersMap = {
  root: `/`,
  login: `/login`,
  waitlist: `/waitlist`,
  closebeta: `/closebeta`,
  noWorkspace: `/no-workspace`,
  workspace: `/workspace/:workspaceId?`,
  dashboard: `/workspace/:workspaceId?/dashboard`,
  fineTuneCreate: `/workspace/:workspaceId?/fine-tune/create`,
  settingsGeneral: `/workspace/:workspaceId?/settings/general`,
  settingsAPITokens: `/workspace/:workspaceId?/settings/api-tokens`,
  settingsSecrets: `/workspace/:workspaceId?/settings/secrets`,
  photonsList: `/workspace/:workspaceId?/photons/list`,
  photonVersions: `/workspace/:workspaceId?/photons/versions/:name`,
  photonDetail: `/workspace/:workspaceId?/photons/detail/:photonId`,
  deploymentsList: `/workspace/:workspaceId?/deployments/list/:photonId?`,
  deploymentDetail: `/workspace/:workspaceId?/deployments/detail/:deploymentId`,
  deploymentDetailDemo: `/workspace/:workspaceId?/deployments/detail/:deploymentId/demo`,
  deploymentDetailReplicasList: `/workspace/:workspaceId?/deployments/detail/:deploymentId/replicas/list`,
  deploymentDetailReplicasDetail: `/workspace/:workspaceId?/deployments/detail/:deploymentId/replicas/detail/:replicaId`,
  deploymentDetailReplicasTerminal: `/workspace/:workspaceId?/deployments/detail/:deploymentId/replicas/detail/:replicaId/terminal`,
} as const;

@Injectable()
export class NavigateService {
  private navigateTo$ = new Subject<[To, NavigateOptions?]>();
  private navigated$ = new Subject<string>();

  constructor(private workspaceTrackerService: WorkspaceTrackerService) {}
  private navigate(to: To, options?: NavigateOptions) {
    this.navigateTo$.next([to, options]);
  }

  onNavigate() {
    return this.navigateTo$.asObservable();
  }

  onNavigated(): Observable<string> {
    return this.navigated$.asObservable();
  }

  emitNavigated(pathname: string) {
    this.navigated$.next(pathname);
  }

  navigateTo<T extends keyof Routers>(
    name: T,
    ...[paramsOrOptions, optionsOrNull]: IsOptionalParams<T> extends true
      ? IsNoParams<T> extends true
        ? [undefined | null, NavigateToOptions] | [NavigateToOptions] | []
        :
            | [NullablePathParams<T>, NavigateToOptions]
            | [NullablePathParams<T>]
            | []
      : [NullablePathParams<T>, NavigateToOptions] | [NullablePathParams<T>]
  ) {
    let options: NavigateToOptions;
    let params: NullablePathParams<T>;
    const hasParams = RoutersMap[name].includes(":");
    if (hasParams) {
      options = optionsOrNull ?? {};
      params = (paramsOrOptions || null) as NullablePathParams<T>;
    } else {
      if (typeof paramsOrOptions === "object" && paramsOrOptions !== null) {
        options = paramsOrOptions;
      } else {
        options = optionsOrNull ?? {};
      }
      params = null as NullablePathParams<T>;
    }
    const { query, ...restOptions } = options;
    const search =
      query instanceof URLSearchParams
        ? query.toString()
        : query?.replace(/^\?/, "") ?? "";
    const path = `${this.getPath(name, params)}${search ? `?${search}` : ""}`;
    this.navigate(path, restOptions);
  }

  isActive<T extends keyof Routers>(name: T, pathname: string): boolean {
    const path = RoutersMap[name];
    return matchPath({ path, end: false }, pathname) !== null;
  }

  getPath<T extends keyof Routers>(
    name: T,
    // Make optional params when all params are optional
    ...[params]: IsOptionalParams<T> extends true
      ? [NullablePathParams<T>] | []
      : [NullablePathParams<T>]
  ): PathStringLiteral<Routers[T]> {
    let paths = RoutersMap[name].split("/");
    const hasWorkspaceId = paths.includes(":workspaceId?");
    if (params || hasWorkspaceId) {
      const forceParams = (params ?? {}) as PathParams<T>;
      paths = paths
        .map((component) => {
          if (component.startsWith(":")) {
            const key = component.replace(/[:?]/g, "");
            if (
              key === "workspaceId" &&
              !forceParams[key as keyof PathParams<T>]
            ) {
              return this.workspaceTrackerService.id ?? "";
            }
            return forceParams[key as keyof PathParams<T>] ?? "";
          }
          return component;
        })
        .filter((e, i) => e || i === 0);
    }

    return paths.join("/") as PathStringLiteral<Routers[T]>;
  }
}
