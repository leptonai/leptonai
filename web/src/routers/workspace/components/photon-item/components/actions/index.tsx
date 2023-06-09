import { FC } from "react";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import { App, Button, Divider, Popconfirm, Space } from "antd";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Download } from "@carbon/icons-react";
import { DeleteOutlined } from "@ant-design/icons";
import { CreateDeployment } from "@lepton-dashboard/routers/workspace/components/create-deployment";

export const Actions: FC<{ photon: Photon; extraActions: boolean }> = ({
  photon,
  extraActions = false,
}) => {
  const { message } = App.useApp();
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
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
            <Button danger size="small" type="text" icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </>
      )}
    </Space>
  );
};
