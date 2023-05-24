import { FC, PropsWithChildren, useContext } from "react";
import { Injector, Provider, ReflectiveInjector } from "injection-js";
import { useOnce } from "@lepton-libs/hooks/use-once";
import { InjectorContext } from "./context";

export const DIContainer: FC<
  PropsWithChildren<{
    providers: Provider[];
  }>
> = ({ children, providers }) => {
  const rootInjector = useContext(InjectorContext) as ReflectiveInjector;
  const contextInjector = useOnce(() => {
    if (rootInjector === Injector.NULL) {
      return ReflectiveInjector.resolveAndCreate(providers);
    }
    return rootInjector.resolveAndCreateChild(providers);
  });
  return (
    <InjectorContext.Provider value={contextInjector}>
      {children}
    </InjectorContext.Provider>
  );
};
