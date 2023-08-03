import { StopFilledAlt } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import { App, Button, Popconfirm } from "antd";
import { FC } from "react";

export const Terminate: FC<{ name: string }> = ({ name }) => {
  const { message } = App.useApp();
  const tunaService = useInject(TunaService);
  const refreshService = useInject(RefreshService);

  return (
    <Popconfirm
      title="Stop the tuna"
      description="Are you sure to stop?"
      onConfirm={() => {
        void message.loading({
          content: `Stopping tuna, please wait...`,
          key: "stop-tuna",
          duration: 0,
        });
        tunaService.deleteInference(name).subscribe({
          next: () => {
            message.destroy("stop-tuna");
            void message.success(`Successfully stopped`);
            refreshService.refresh();
          },
          error: () => {
            message.destroy("stop-tuna");
          },
        });
      }}
    >
      <Button
        size="small"
        type="text"
        icon={<CarbonIcon icon={<StopFilledAlt />} />}
      >
        Stop
      </Button>
    </Popconfirm>
  );
};
