import { Copy } from "@carbon/icons-react";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, useMemo, useState } from "react";
import { App, Button, Empty, Modal, Space } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { PlusOutlined } from "@ant-design/icons";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { DeploymentForm } from "@lepton-dashboard/routers/workspace/components/deployment-form";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";

const CreateDeploymentDetail: FC<{
  finish: () => void;
  photonId?: string;
  fork?: Deployment;
}> = ({ finish, photonId, fork }) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const hardwareService = useInject(HardwareService);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromBehaviorSubject(deploymentService.list());
  const photonGroups = useStateFromBehaviorSubject(photonService.listGroups());

  const initialDeployment: Partial<Deployment> = {
    name: fork?.name || "",
    photon_id: fork?.photon_id || photonId,
    resource_requirement: fork?.resource_requirement || {
      min_replicas: 1,
      resource_shape: hardwareService.shapes[0],
    },
    api_tokens: fork?.api_tokens || [
      { value_from: { token_name_ref: "WORKSPACE_TOKEN" } },
    ],
    envs: fork?.envs || [],
    mounts: fork?.mounts || [],
    pull_image_secrets: fork?.pull_image_secrets || [],
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

export const CreateDeployment: FC<{
  min?: boolean;
  photonId?: string;
  fork?: Deployment;
}> = ({ min = false, photonId, fork }) => {
  const [open, setOpen] = useState(false);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const openLayer = () => {
    setOpen(true);
  };
  const close = () => {
    setOpen(false);
  };

  const button = useMemo(() => {
    if (fork) {
      return (
        <Button
          size="small"
          type="text"
          icon={<CarbonIcon icon={<Copy />} />}
          disabled={workspaceTrackerService.workspace?.isPastDue}
          onClick={openLayer}
        >
          Clone
        </Button>
      );
    } else {
      if (min) {
        return (
          <Button
            size="small"
            type="text"
            icon={<DeploymentIcon />}
            disabled={workspaceTrackerService.workspace?.isPastDue}
            onClick={openLayer}
          >
            Deploy
          </Button>
        );
      } else {
        return (
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            disabled={workspaceTrackerService.workspace?.isPastDue}
            onClick={openLayer}
          >
            Create deployment
          </Button>
        );
      }
    }
  }, [min, fork, workspaceTrackerService.workspace?.isPastDue]);
  return (
    <>
      {button}
      <Modal
        destroyOnClose
        title="Create deployment"
        open={open}
        onCancel={close}
        footer={null}
      >
        <CreateDeploymentDetail
          fork={fork}
          photonId={photonId}
          finish={close}
        />
      </Modal>
    </>
  );
};
