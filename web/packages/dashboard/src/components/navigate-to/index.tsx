import {
  Navigate as ReactRouterNavigate,
  NavigateProps,
} from "react-router-dom";
import {
  IsOptionalParams,
  NavigateService,
  NullablePathParams,
  Routers,
} from "@lepton-dashboard/services/navigate.service";
import { useMemo } from "react";
import { useInject } from "@lepton-libs/di";

export type NamedNavigateProp<T extends keyof Routers> =
  IsOptionalParams<T> extends true
    ? {
        name: T;
        params?: NullablePathParams<T>;
        query?: string | URLSearchParams;
      } & Pick<NavigateProps, "replace" | "state" | "relative">
    : {
        name: T;
        params: NullablePathParams<T>;
        query?: string | URLSearchParams;
      } & Pick<NavigateProps, "replace" | "state" | "relative">;

export function NavigateTo<T extends keyof Routers>(
  props: NamedNavigateProp<T>
) {
  const { replace, state, relative } = props;
  const navigateService = useInject(NavigateService);
  const path = useMemo(() => {
    const search =
      props.query instanceof URLSearchParams
        ? props.query.toString()
        : props.query?.replace(/^\?/, "") ?? "";
    return `${navigateService.getPath(
      props.name,
      (props?.params || null) as NullablePathParams<T>
    )}${search ? `?${search}` : ""}`;
  }, [navigateService, props]);

  return (
    <ReactRouterNavigate
      to={path!}
      replace={replace}
      state={state}
      relative={relative}
    />
  );
}
