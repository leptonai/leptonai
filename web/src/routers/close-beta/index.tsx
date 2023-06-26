import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { Typography } from "antd";
import { FC } from "react";

export const CloseBeta: FC = () => {
  useDocumentTitle("Close Beta");

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
