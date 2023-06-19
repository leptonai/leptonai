import { useInject } from "@lepton-libs/di";
import { useEffect } from "react";
import { InitializerService } from "@lepton-dashboard/services/initializer.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";

export const useInitialize = () => {
  const initializerService = useInject(InitializerService);
  const initialized = useStateFromBehaviorSubject(
    initializerService.initialized$
  );
  useEffect(() => {
    initializerService.bootstrap();
  }, [initializerService]);
  return initialized;
};
