import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { Portal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/portal";
import { Typography } from "antd";
import { FC } from "react";

export const Payment: FC<{ paymentMethodAttached: boolean }> = ({
  paymentMethodAttached,
}) => {
  return (
    <Card>
      <Typography.Title
        level={4}
        css={css`
          margin-top: 0;
          margin-bottom: 4px !important;
        `}
      >
        PAYMENT
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        Change how you pay.
      </Typography.Paragraph>
      <Portal paymentMethodAttached={paymentMethodAttached} />
    </Card>
  );
};
