import { FC, useEffect } from "react";
import { useInject } from "@lepton-libs/di";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { useLocation, useNavigate } from "react-router-dom";

export const Navigator: FC = () => {
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
  return null;
};
