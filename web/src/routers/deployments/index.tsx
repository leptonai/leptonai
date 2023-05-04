import { FC, useEffect } from "react";
import { useInject } from "@lepton-libs/di";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";

export const Deployments: FC = () => {
  const titleService = useInject(TitleService);
  useEffect(() => {
    titleService.setTitle("Deployments");
  }, [titleService]);
  return <div />;
};
