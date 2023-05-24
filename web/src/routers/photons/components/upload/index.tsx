import { FC, useState } from "react";
import { App, Button, Upload as AntdUpload, UploadFile } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { RcFile } from "antd/es/upload";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";

export const Upload: FC = () => {
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const beforeUpload = (file: UploadFile) => {
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file as RcFile);
    photonService.create(formData).subscribe({
      next: () => {
        setLoading(false);
        refreshService.refresh();
        void message.success("Upload photon success");
      },
      error: () => {
        setLoading(false);
      },
    });
    return false;
  };
  return (
    <AntdUpload
      fileList={[]}
      beforeUpload={beforeUpload}
      style={{ width: "100%" }}
    >
      <Button type="primary" icon={<UploadOutlined />} block loading={loading}>
        Upload Photon
      </Button>
    </AntdUpload>
  );
};
