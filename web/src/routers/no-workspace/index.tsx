import { FC, useEffect } from "react";
import { Typography } from "antd";
import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useInject } from "@lepton-libs/di";
import { TitleService } from "@lepton-dashboard/services/title.service";

export const NoWorkspace: FC = () => {
  const titleService = useInject(TitleService);

  useEffect(() => {
    titleService.setTitle("Workspace Unavailable");
  }, [titleService]);
  return (
    <SignAsOther
      tips={
        <Typography.Title level={3}>Workspace is not ready</Typography.Title>
      }
    />
  );
};
