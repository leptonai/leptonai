import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { FC, useCallback } from "react";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { App, Button, Popconfirm, Space, Tooltip } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Download, TrashCan } from "@carbon/icons-react";
import { CreateDeployment } from "@lepton-dashboard/routers/workspace/components/create-deployment";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";

export const Actions: FC<{
  photon: Photon;
  extraActions: boolean;
  relatedDeployments?: Deployment[];
}> = ({ photon, extraActions = false, relatedDeployments = [] }) => {
  const { message } = App.useApp();
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);

  const downloadPhoton = useCallback(() => {
    const url = photonService.getDownloadUrlById(photon.id);
    const token = workspaceTrackerService.workspace?.auth.token;
    fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }).then((res) => {
      res.blob().then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${photon.id}.photon.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
    });
  }, [photon, photonService, workspaceTrackerService]);

  const deleteButton = (
    <Button
      disabled={relatedDeployments.length > 0}
      size="small"
      type="text"
      icon={<CarbonIcon icon={<TrashCan />} />}
    >
      Delete
    </Button>
  );
  return (
    <Space wrap size={[12, 4]}>
      <CreateDeployment photonId={photon.id} min />
      {extraActions && (
        <>
          <Button
            icon={<CarbonIcon icon={<Download />} />}
            type="text"
            size="small"
            onClick={downloadPhoton}
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
