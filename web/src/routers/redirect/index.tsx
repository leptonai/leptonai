import { useSearchParams } from "react-router-dom";
import { useEffect } from "react";
import { useInject } from "@lepton-libs/di";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

export const Redirect = () => {
  const [params] = useSearchParams();
  const navigateService = useInject(NavigateService);
  const redirectTo = params.get("to");

  useEffect(() => {
    let url: URL | null;
    try {
      url = redirectTo ? new URL(decodeURIComponent(redirectTo)) : null;
    } catch (e) {
      console.error(e);
      url = null;
    }
    if (
      url &&
      (url.hostname === "localhost" || url.hostname.endsWith("lepton.ai"))
    ) {
      window.location.href = url.toString();
    } else {
      navigateService.navigateTo("root");
    }
  }, [navigateService, redirectTo]);

  return null;
};
