import { TitleService } from "@lepton-dashboard/services/title.service";
import { useInject } from "@lepton-libs/di";
import { useEffect } from "react";

export const useDocumentTitle = (title: string) => {
  const titleService = useInject(TitleService);

  useEffect(() => {
    titleService.setTitle(title);
  }, [title, titleService]);
};
