import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC } from "react";
import { Typography } from "antd";
import { SignAsOther } from "@lepton-dashboard/components/signin-other";

export const NoWorkspace: FC = () => {
  useDocumentTitle("Workspace Unavailable");

  return (
    <SignAsOther
      tips={
        <Typography.Title level={3}>Workspace is not ready</Typography.Title>
      }
    />
  );
};
