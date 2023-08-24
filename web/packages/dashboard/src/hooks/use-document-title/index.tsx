import { MetaService } from "@lepton-dashboard/services/meta.service";
import { useInject } from "@lepton-libs/di";
import { useEffect } from "react";

export const useDocumentTitle = (title: string) => {
  const metaService = useInject(MetaService);

  useEffect(() => {
    metaService.setTitle(title);
  }, [title, metaService]);
};
