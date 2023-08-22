import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { useInject } from "@lepton-libs/di";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export const UseSetupNavigate = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const navigateService = useInject(NavigateService);

  useEffect(() => {
    navigateService.emitNavigated(location.pathname);
  }, [location.pathname, navigateService]);

  useEffect(() => {
    const subscription = navigateService.onNavigate().subscribe((args) => {
      navigate(...args);
    });
    return () => {
      subscription.unsubscribe();
    };
  }, [navigateService, navigate]);
};
