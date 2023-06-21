import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { FC } from "react";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { App, Button, Divider, Popconfirm, Space, Tooltip } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Download, TrashCan } from "@carbon/icons-react";
import { CreateDeployment } from "@lepton-dashboard/routers/workspace/components/create-deployment";

export const Actions: FC<{
  photon: Photon;
  extraActions: boolean;
  relatedDeployments?: Deployment[];
}> = ({ photon, extraActions = false, relatedDeployments = [] }) => {
  const { message } = App.useApp();
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const deleteButton = (
    <Button
      disabled={relatedDeployments.length > 0}
      danger
      size="small"
      type="text"
      icon={<CarbonIcon icon={<TrashCan />} />}
    >
      Delete
    </Button>
  );
  return (
    <Space size={0} split={<Divider type="vertical" />}>
      <CreateDeployment photonId={photon.id} min />
      {extraActions && (
        <>
          <Button
            icon={<CarbonIcon icon={<Download />} />}
            type="text"
            size="small"
            href={photonService.getDownloadUrlById(photon.id)}
            download
          >
            Download
          </Button>
          <Popconfirm
            disabled={relatedDeployments.length > 0}
            title="Delete the photon"
            description="Are you sure to delete?"
            onConfirm={() => {
              void message.loading({
                content: `Deleting photon ${photon.id}, please wait...`,
                key: "delete-photon",
                duration: 0,
              });
              photonService.delete(photon.id).subscribe({
                next: () => {
                  message.destroy("delete-photon");
                  void message.success(
                    `Successfully deleted photon ${photon.id}`
                  );
                  refreshService.refresh();
                },
                error: () => {
                  message.destroy("delete-photon");
                },
              });
            }}
          >
            {relatedDeployments.length > 0 ? (
              <Tooltip title="Cannot delete a currently deployed version">
                {deleteButton}
              </Tooltip>
            ) : (
              deleteButton
            )}
          </Popconfirm>
        </>
      )}
    </Space>
  );
};
