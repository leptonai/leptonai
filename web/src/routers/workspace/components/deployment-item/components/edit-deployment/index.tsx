import { FC, useState } from "react";
import { App, Button, Drawer, Empty, Space } from "antd";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Edit as EditIcon } from "@carbon/icons-react";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentForm } from "@lepton-dashboard/routers/workspace/components/deployment-form";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map } from "rxjs";

const EditDeploymentDetail: FC<{
  deployment: Deployment;
  close: () => void;
}> = ({ deployment, close }) => {
  const { message } = App.useApp();
  const deploymentService = useInject(DeploymentService);
  const photonService = useInject(PhotonService);

  const photonGroups = useStateFromObservable(
    () =>
      photonService.listGroups().pipe(
        map((v) => {
          return v.filter((g) =>
            g.versions.some((v) => v.id === deployment.photon_id)
          );
        })
      ),
    []
  );

  const updateDeployment = (value: Partial<Deployment>) => {
    void message.loading({
      content: "Updating deployment, please wait...",
      duration: 0,
      key: "update-deployment",
    });
    deploymentService.update(deployment.id, value).subscribe({
      next: () => {
        message.destroy("update-deployment");
        close();
      },
      error: () => {
        message.destroy("update-deployment");
      },
    });
  };
  return photonGroups.length ? (
    <DeploymentForm
      photonGroups={photonGroups}
      deployments={[]}
      edit
      buttons={
        <Space>
          <Button type="primary" htmlType="submit">
            Save
          </Button>
          <Button onClick={close}>Cancel</Button>
        </Space>
      }
      initialDeploymentValue={deployment}
      submit={(v) => updateDeployment(v)}
    />
  ) : (
    <Empty description="No assicoiated photons found" />
  );
};

export const EditDeployment: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const [open, setOpen] = useState(false);
  const refreshService = useInject(RefreshService);

  const openDrawer = () => {
    setOpen(true);
  };
  const closeDrawer = () => {
    setOpen(false);
    refreshService.refresh();
  };

  return (
    <>
      <Button
        type="text"
        size="small"
        icon={<CarbonIcon icon={<EditIcon />} />}
        onClick={openDrawer}
      >
        Edit
      </Button>
      <Drawer
        destroyOnClose
        size="large"
        contentWrapperStyle={{ maxWidth: "100%" }}
        title="Edit deployment"
        open={open}
        onClose={closeDrawer}
      >
        <EditDeploymentDetail close={closeDrawer} deployment={deployment} />
      </Drawer>
    </>
  );
};
