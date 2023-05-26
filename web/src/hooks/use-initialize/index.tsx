import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import { InitializerService } from "@lepton-dashboard/services/initializer.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";

export const useInitialize = () => {
  const refreshService = useInject(RefreshService);
  const location = useLocation();
  useEffect(() => {
    refreshService.integrateWithRouter(location.pathname);
  }, [location.pathname, refreshService]);
  const initializerService = useInject(InitializerService);
  const initialized = useStateFromBehaviorSubject(
    initializerService.initialized$
  );
  useEffect(() => {
    initializerService.bootstrap();
  }, [initializerService]);
  return initialized;
};
