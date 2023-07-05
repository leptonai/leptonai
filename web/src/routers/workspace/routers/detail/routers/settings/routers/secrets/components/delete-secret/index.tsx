import { TrashCan } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { DeploymentSecretEnv } from "@lepton-dashboard/interfaces/deployment";
import { DeploymentMinTable } from "@lepton-dashboard/routers/workspace/components/deployment-min-table";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FC } from "react";
import { App, Button, Popconfirm, Popover } from "antd";
import { useInject } from "@lepton-libs/di";
import { map } from "rxjs";

export const DeleteSecret: FC<{
  secret: string;
}> = ({ secret }) => {
  const deploymentService = useInject(DeploymentService);
  const { message } = App.useApp();
  const refreshService = useInject(RefreshService);
  const secretService = useInject(SecretService);
  const deployments = useStateFromObservable(
    () =>
      deploymentService
        .list()
        .pipe(
          map((list) =>
            list.filter((item) =>
              item.envs?.some(
                (e) =>
                  (e as DeploymentSecretEnv).value_from.secret_name_ref ===
                  secret
              )
            )
          )
        ),
    []
  );

  return deployments.length > 0 ? (
    <Popover
      title="Cannot delete a currently used secret, used by:"
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
      title="Delete the secret"
      description="Are you sure to delete?"
      onConfirm={() => {
        void message.loading({
          content: `Deleting secret ${secret}, please wait...`,
          key: "delete-secret",
          duration: 0,
        });
        secretService.deleteSecret(secret).subscribe({
          next: () => {
            message.destroy("delete-secret");
            void message.success(`Successfully deleted secret ${secret}`);
            refreshService.refresh();
          },
          error: () => {
            message.destroy("delete-secret");
          },
        });
      }}
    >
      <Button
        type="text"
        size="small"
        danger
        icon={<CarbonIcon icon={<TrashCan />} />}
      >
        Delete
      </Button>
    </Popconfirm>
  );
};
