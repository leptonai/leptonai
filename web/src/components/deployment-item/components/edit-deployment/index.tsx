import { FC, useState } from "react";
import {
  App,
  Button,
  Descriptions,
  Drawer,
  InputNumber,
  Select,
  Space,
  Typography,
} from "antd";
import { DeploymentStatus } from "@lepton-dashboard/components/deployment-status";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { mergeMap, of } from "rxjs";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Edit as EditIcon } from "@carbon/icons-react";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import dayjs from "dayjs";

const EditDeploymentDetail: FC<{
  deployment: Deployment;
  close: () => void;
}> = ({ deployment, close }) => {
  const { message } = App.useApp();
  const photonService = useInject(PhotonService);
  const deploymentService = useInject(DeploymentService);
  const photon = useStateFromObservable(
    () =>
      deploymentService
        .id(deployment.id!)
        .pipe(
          mergeMap((deployment) =>
            deployment ? photonService.id(deployment.photon_id) : of(undefined)
          )
        ),
    undefined,
    {
      next: (v) => setPhotonId(v?.id),
    }
  );
  const photon$ = useObservableFromState(photon);
  const photonList = useStateFromObservable(
    () =>
      photon$.pipe(
        mergeMap((p) => (p ? photonService.listByName(p.name) : of([])))
      ),
    []
  );
  const [minReplicas, setMinReplicas] = useState<number | null>(
    deployment?.resource_requirement?.min_replicas ?? null
  );
  const [photonId, setPhotonId] = useState<string | undefined>(undefined);

  return (
    <>
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="Name">{deployment.name}</Descriptions.Item>
        <Descriptions.Item label="ID">{deployment.id}</Descriptions.Item>
        <Descriptions.Item label="Status">
          <DeploymentStatus status={deployment.status.state} />
        </Descriptions.Item>
        <Descriptions.Item label="Photon Name">
          {photon?.name}
        </Descriptions.Item>
        <Descriptions.Item label="Photon Version">
          <Select
            style={{ width: "100%" }}
            value={photonId}
            onChange={(v) => setPhotonId(v)}
            options={photonList.map((p) => {
              return {
                label: `${dayjs(p.created_at).format("LLLL")}`,
                value: p.id,
              };
            })}
          />
        </Descriptions.Item>
        <Descriptions.Item label="Created At">
          <DateParser date={deployment.created_at} detail />
        </Descriptions.Item>
        <Descriptions.Item label="External Endpoint">
          <Typography.Text copyable>
            {deployment.status.endpoint.external_endpoint || "-"}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Internal Endpoint">
          <Typography.Text copyable>
            {deployment.status.endpoint.internal_endpoint || "-"}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="CPU">
          {deployment.resource_requirement.cpu}
        </Descriptions.Item>
        <Descriptions.Item label="Memory">
          {deployment.resource_requirement.memory} MB
        </Descriptions.Item>
        <Descriptions.Item label="Accelerator">
          {deployment.resource_requirement.accelerator_type || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Accelerator Number">
          {deployment.resource_requirement.accelerator_num || "-"}
        </Descriptions.Item>

        <Descriptions.Item label="Min Replicas">
          <InputNumber
            autoFocus
            value={minReplicas}
            min={0}
            onChange={(e) => setMinReplicas(e)}
          />
        </Descriptions.Item>
      </Descriptions>
      <Space style={{ marginTop: "24px" }}>
        <Button
          type="primary"
          onClick={() => {
            if (minReplicas !== null && minReplicas !== undefined && photonId) {
              void message.loading({
                content: "Update deployment, please wait...",
                duration: 0,
                key: "update-deployment",
              });
              deploymentService
                .update(deployment.id, {
                  photon_id: photonId,
                  resource_requirement: { min_replicas: minReplicas },
                })
                .subscribe({
                  next: () => {
                    message.destroy("update-deployment");
                    close();
                  },
                  error: () => {
                    message.destroy("update-deployment");
                  },
                });
            }
          }}
        >
          Save
        </Button>
        <Button onClick={close}>Cancel</Button>
      </Space>
    </>
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
        title={deployment.name}
        open={open}
        onClose={closeDrawer}
      >
        <EditDeploymentDetail close={closeDrawer} deployment={deployment} />
      </Drawer>
    </>
  );
};
