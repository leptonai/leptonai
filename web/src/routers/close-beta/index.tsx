import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { useInject } from "@lepton-libs/di";
import { Typography } from "antd";
import { FC, useEffect } from "react";

export const CloseBeta: FC = () => {
  const titleService = useInject(TitleService);

  useEffect(() => {
    titleService.setTitle("Close Beta");
  }, [titleService]);
  return (
    <SignAsOther
      tips={
        <>
          <Typography.Title level={3}>
            We are currently in closed beta
          </Typography.Title>
          <Typography.Paragraph>
            Thank you for your interest
          </Typography.Paragraph>
        </>
      }
    />
  );
};
