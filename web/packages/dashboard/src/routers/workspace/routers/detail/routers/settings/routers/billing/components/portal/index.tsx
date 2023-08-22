import { Launch } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { BillingService } from "@lepton-dashboard/routers/workspace/services/billing.service";
import { useInject } from "@lepton-libs/di";
import { Button } from "antd";
import { FC, useState } from "react";

export const Portal: FC<{ paymentMethodAttached: boolean }> = ({
  paymentMethodAttached,
}) => {
  const [loading, setLoading] = useState(false);
  const billingService = useInject(BillingService);

  const jumpToPortal = () => {
    setLoading(true);
    billingService.getPortal().subscribe(({ url }) => {
      window.open(url);
      setLoading(false);
    });
  };
  return (
    <Button
      icon={<CarbonIcon icon={<Launch />} />}
      size="small"
      loading={loading}
      type="primary"
      onClick={() => jumpToPortal()}
    >
      {paymentMethodAttached
        ? "Manage payment method"
        : "Add new payment method"}
    </Button>
  );
};
