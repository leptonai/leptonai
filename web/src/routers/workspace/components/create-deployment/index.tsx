import { LinkTo } from "@lepton-dashboard/components/link-to";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, useState } from "react";
import { App, Button, Empty, Modal, Space } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { PlusOutlined } from "@ant-design/icons";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { DeploymentForm } from "@lepton-dashboard/routers/workspace/components/deployment-form";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";

const CreateDeploymentDetail: FC<{ finish: () => void; photonId?: string }> = ({
  finish,
  photonId,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const hardwareService = useInject(HardwareService);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromBehaviorSubject(deploymentService.list());
  const photonGroups = useStateFromBehaviorSubject(photonService.listGroups());

  const initialDeployment: Partial<Deployment> = {
    photon_id: photonId,
    resource_requirement: {
      min_replicas: 1,
      resource_shape: hardwareService.shapes[0],
    },
    api_tokens: [{ value_from: { token_name_ref: "WORKSPACE_TOKEN" } }],
    envs: [],
    mounts: [],
    pull_image_secrets: [],
  };
  const createDeployment = (deployment: Partial<Deployment>) => {
    setLoading(true);
    void message.loading({
      content: "Creating deployment, please wait ...",
      key: "create-deployment-deployment",
      duration: 0,
    });
    deploymentService.create(deployment).subscribe({
      next: (deployment) => {
        message.destroy("create-deployment-deployment");
        void message.success(
          <LinkTo
            name="deploymentDetail"
            params={{ deploymentName: deployment.name }}
          >
            Create deployment success
          </LinkTo>
        );
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
        <Space>
          <Button loading={loading} type="primary" htmlType="submit">
            Create
          </Button>
        </Space>
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
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const openLayer = () => {
    setOpen(true);
  };
  const close = () => {
    setOpen(false);
  };

  return (
    <>
      {min ? (
        <Button
          size="small"
          type="text"
          icon={<DeploymentIcon />}
          disabled={workspaceTrackerService.workspace?.isPastDue}
          onClick={openLayer}
        >
          Deploy
        </Button>
      ) : (
        <Button
          type="primary"
          block
          icon={<PlusOutlined />}
          disabled={workspaceTrackerService.workspace?.isPastDue}
          onClick={openLayer}
        >
          Create deployment
        </Button>
      )}
      <Modal
        destroyOnClose
        title="Create deployment"
        open={open}
        onCancel={close}
        footer={null}
      >
        <CreateDeploymentDetail photonId={photonId} finish={close} />
      </Modal>
    </>
  );
};
