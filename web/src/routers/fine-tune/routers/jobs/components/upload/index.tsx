import { FC, useState } from "react";
import { App, Button, Upload as AntdUpload } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { FineTuneService } from "@lepton-dashboard/routers/fine-tune/services/fine-tune.service";

export const Upload: FC = () => {
  const fineTuneService = useInject(FineTuneService);
  const refreshService = useInject(RefreshService);
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const beforeUpload = (file: File) => {
    setLoading(true);
    fineTuneService.creatJob(file).subscribe({
      next: () => {
        setLoading(false);
        refreshService.refresh();
        void message.success("Upload JSON success");
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
        Upload JSON
      </Button>
    </AntdUpload>
  );
};
