import { TrashCan } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import { App, Button, Popconfirm } from "antd";
import { FC } from "react";
import { matchPath } from "react-router-dom";

export const DeleteDeployment: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const { message } = App.useApp();
  const navigateService = useInject(NavigateService);
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  return (
    <Popconfirm
      title="Delete the deployment"
      description="Are you sure to delete?"
      onConfirm={() => {
        void message.loading({
          content: `Deleting deployment ${deployment.name}, please wait...`,
          key: "delete-deployment",
          duration: 0,
        });
        deploymentService.delete(deployment.name).subscribe({
          next: () => {
            message.destroy("delete-deployment");
            void message.success(
              `Successfully deleted deployment ${deployment.name}`
            );
            refreshService.refresh();
            if (
              matchPath(
                {
                  path: navigateService.getPath("deploymentDetail", {
                    deploymentName: deployment.name,
                  }),
                  end: false,
                },
                location.pathname
              )
            ) {
              navigateService.navigateTo("deploymentsList", null, {
                relative: "route",
              });
            }
          },
          error: () => {
            message.destroy("delete-deployment");
          },
        });
      }}
    >
      <Button
        type="text"
        size="small"
        icon={<CarbonIcon icon={<TrashCan />} />}
      >
        Delete
      </Button>
    </Popconfirm>
  );
};
