import { TrashCan } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { DeploymentMinTable } from "@lepton-dashboard/routers/workspace/components/deployment-min-table";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FC } from "react";
import { App, Button, Popconfirm, Popover } from "antd";
import { useInject } from "@lepton-libs/di";
import { map } from "rxjs";
import { ImagePullSecretService } from "@lepton-dashboard/routers/workspace/services/image-pull-secret.service";

export const DeleteRegistry: FC<{
  name: string;
}> = ({ name }) => {
  const deploymentService = useInject(DeploymentService);
  const { message } = App.useApp();
  const refreshService = useInject(RefreshService);
  const imagePullSecretService = useInject(ImagePullSecretService);
  const deployments = useStateFromObservable(
    () =>
      deploymentService
        .list()
        .pipe(
          map((list) =>
            list.filter((item) =>
              (item.pull_image_secrets || []).some((_name) => _name === name)
            )
          )
        ),
    []
  );

  return deployments.length > 0 ? (
    <Popover
      title="Cannot delete a currently used registry, used by:"
      placement="bottomLeft"
      content={<DeploymentMinTable deployments={deployments} />}
    >
      <Button
        disabled
        type="text"
        size="small"
        danger
        icon={<CarbonIcon icon={<TrashCan />} />}
      >
        Delete
      </Button>
    </Popover>
  ) : (
    <Popconfirm
      title="Delete the registry"
      description="Are you sure to delete?"
      onConfirm={() => {
        void message.loading({
          content: `Deleting registry ${name}, please wait...`,
          key: "delete-registry",
          duration: 0,
        });
        imagePullSecretService.deleteImagePullSecret(name).subscribe({
          next: () => {
            message.destroy("delete-registry");
            void message.success(`Successfully deleted registry ${name}`);
            refreshService.refresh();
          },
          error: () => {
            message.destroy("delete-registry");
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
