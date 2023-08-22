import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC } from "react";
import { SignAsOther } from "@lepton-dashboard/components/signin-other";

export const NoWorkspace: FC = () => {
  useDocumentTitle("Workspace Unavailable");

  return <SignAsOther heading="Workspace is not ready" />;
};
