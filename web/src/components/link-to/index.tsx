import { Link } from "@lepton-dashboard/components/link";
import {
  IsOptionalParams,
  NavigateService,
  NullablePathParams,
  Routers,
} from "@lepton-dashboard/services/navigate.service";
import { RelativeRoutingType } from "react-router-dom";
import { ReactNode, Ref, useMemo, forwardRef } from "react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { useInject } from "@lepton-libs/di";

type LinkProps = {
  underline?: boolean;
  target?: string;
  relative?: RelativeRoutingType;
  icon?: ReactNode;
  ref?: Ref<HTMLAnchorElement>;
  children?: ReactNode;
} & EmotionProps;

type LinkToProps<T extends keyof Routers> = IsOptionalParams<T> extends true
  ? {
      name: T;
      params?: NullablePathParams<T>;
    } & LinkProps
  : {
      name: T;
      params: NullablePathParams<T>;
    } & LinkProps;

const LinkToComp = <T extends keyof Routers>({
  name,
  params,
  children,
  target,
  relative = "path",
  icon,
  className,
  underline = true,
  css,
  ref,
}: LinkToProps<T>) => {
  const navigateService = useInject(NavigateService);
  const path = useMemo(() => {
    return navigateService.getPath(
      name,
      (params || null) as NullablePathParams<T>
    );
  }, [navigateService, name, params]);

  return (
    <Link
      className={className}
      underline={underline}
      icon={icon}
      css={css}
      ref={ref}
      to={path}
      target={target}
      relative={relative}
    >
      {children}
    </Link>
  );
};

export const LinkTo = forwardRef(LinkToComp) as unknown as <
  T extends keyof Routers
>(
  props: LinkToProps<T> & { ref?: React.ForwardedRef<HTMLUListElement> }
) => ReturnType<typeof LinkToComp<T>>;
