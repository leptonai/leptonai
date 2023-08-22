import { InjectionToken } from "injection-js";
import { useContext } from "react";
import { InjectorContext } from "./context";

type Constructor<T> = Function & { prototype: T };

export function useInject<T>(
  token: Constructor<T> | InjectionToken<T>,
  notFoundValue?: T
): T {
  return useContext(InjectorContext).get<T>(
    token as unknown as InjectionToken<T>,
    notFoundValue
  );
}
