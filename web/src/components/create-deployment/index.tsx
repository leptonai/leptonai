import { FC, useState } from "react";
import { App, Button, Drawer, Empty } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { PlusOutlined } from "@ant-design/icons";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { DeploymentForm } from "@lepton-dashboard/components/deployment-form";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";

const CreateDeploymentDetail: FC<{ finish: () => void; photonId?: string }> = ({
  finish,
  photonId,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );

  const initialDeployment: Partial<Deployment> = {
    photon_id: photonId,
    resource_requirement: {
      min_replicas: 1,
      cpu: 1,
      memory: 8192,
    },
    envs: [],
  };
  const createDeployment = (deployment: Partial<Deployment>) => {
    setLoading(true);
    void message.loading({
      content: "Creating deployment, please wait ...",
      key: "create-deployment-deployment",
      duration: 0,
    });
    deploymentService.create(deployment).subscribe({
      next: () => {
        message.destroy("create-deployment-deployment");
        void message.success("Create deployment success");
        refreshService.refresh();
        finish();
        setLoading(false);
      },
      error: () => {
        message.destroy("create-deployment-deployment");
        setLoading(false);
      },
    });
  };
  return photonGroups.length ? (
    <DeploymentForm
      photonGroups={photonGroups}
      deployments={deployments}
      buttons={
        <Button loading={loading} type="primary" htmlType="submit">
          Create
        </Button>
      }
      initialDeploymentValue={initialDeployment}
      submit={createDeployment}
    />
  ) : (
    <Empty description="No photons yet, Please upload photon first" />
  );
};

export const CreateDeployment: FC<{ min?: boolean; photonId?: string }> = ({
  min = false,
  photonId,
}) => {
  const [open, setOpen] = useState(false);

  const openDrawer = () => {
    setOpen(true);
  };
  const closeDrawer = () => {
    setOpen(false);
  };

  return (
    <>
      {min ? (
        <Button
          size="small"
          type="text"
          icon={<DeploymentIcon />}
          onClick={openDrawer}
        >
          Deploy
        </Button>
      ) : (
        <Button
          type="primary"
          block
          icon={<PlusOutlined />}
          onClick={openDrawer}
        >
          Create Deployment
        </Button>
      )}
      <Drawer
        destroyOnClose
        size="large"
        contentWrapperStyle={{ maxWidth: "100%" }}
        title="Create Deployment"
        open={open}
        onClose={closeDrawer}
      >
        <CreateDeploymentDetail photonId={photonId} finish={closeDrawer} />
      </Drawer>
    </>
  );
};
