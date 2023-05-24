import { FC, useState } from "react";
import {
  App,
  Button,
  Descriptions,
  Drawer,
  InputNumber,
  Popover,
  Space,
  Typography,
} from "antd";
import { DeploymentStatus } from "@lepton-dashboard/components/deployment-status";
import { PhotonItem } from "@lepton-dashboard/components/photon-item";
import { Link } from "@lepton-dashboard/components/link";
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
export const EditDeployment: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
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
    undefined
  );
  const [minReplicas, setMinReplicas] = useState<number | null>(
    deployment?.resource_requirement?.min_replicas ?? null
  );

  const openDrawer = () => {
    setOpen(true);
    setMinReplicas(deployment?.resource_requirement?.min_replicas ?? null);
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
        title={deployment.name}
        open={open}
        onClose={closeDrawer}
      >
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="Name">{deployment.name}</Descriptions.Item>
          <Descriptions.Item label="ID">{deployment.id}</Descriptions.Item>
          <Descriptions.Item label="Status">
            <DeploymentStatus status={deployment.status.state} />
          </Descriptions.Item>
          <Descriptions.Item label="Photon">
            {photon?.name ? (
              <Popover
                placement="bottomLeft"
                content={<PhotonItem photon={photon} />}
              >
                <span>
                  <Link to={`/photons/versions/${photon?.name}`}>
                    {photon?.name}
                  </Link>
                </span>
              </Popover>
            ) : (
              "-"
            )}
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
              if (minReplicas !== null && minReplicas !== undefined) {
                void message.loading({
                  content: "Update deployment, please wait...",
                  duration: 0,
                  key: "update-deployment",
                });
                deploymentService.update(deployment.id, minReplicas).subscribe({
                  next: () => {
                    message.destroy("update-deployment");
                    closeDrawer();
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
          <Button onClick={closeDrawer}>Cancel</Button>
        </Space>
      </Drawer>
    </>
  );
};
