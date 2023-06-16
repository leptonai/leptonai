import { CloudUpload } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { FineTuneService } from "@lepton-dashboard/routers/fine-tune/services/fine-tune.service";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import {
  App,
  Col,
  Divider,
  Row,
  Spin,
  Typography,
  Upload as AntdUpload,
} from "antd";
import { FC, useState } from "react";

export const Create: FC = () => {
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
        void message.success("Upload file success");
      },
      error: () => {
        setLoading(false);
      },
    });
    return false;
  };
  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card>
          <Spin spinning={loading} tip="Uploading ...">
            <AntdUpload.Dragger fileList={[]} beforeUpload={beforeUpload}>
              <p className="ant-upload-drag-icon">
                <CarbonIcon icon={<CloudUpload />} />
              </p>
              <p className="ant-upload-text">
                Click or drag data to this area to create fine tune job
              </p>
            </AntdUpload.Dragger>
          </Spin>
        </Card>
      </Col>
      <Col span={24}>
        <ThemeProvider token={{ fontSize: 12, padding: 4 }}>
          <Card title="JSON format">
            <Typography.Paragraph>
              <Typography.Text strong>messages</Typography.Text>{" "}
              <Typography.Text type="secondary">array</Typography.Text>
            </Typography.Paragraph>
            <Typography.Paragraph>
              A list of messages comprising the conversation so far.
            </Typography.Paragraph>
            <Card shadowless>
              <Typography.Paragraph>
                <Typography.Text strong>role</Typography.Text>{" "}
                <Typography.Text type="secondary">string</Typography.Text>
              </Typography.Paragraph>
              <Typography.Text>
                The role of the messages author. One of{" "}
                <Typography.Text code>system</Typography.Text>,{" "}
                <Typography.Text code>user</Typography.Text>,{" "}
                <Typography.Text code>assistant</Typography.Text>, or{" "}
                <Typography.Text code>function</Typography.Text>.
              </Typography.Text>
              <Divider
                css={css`
                  margin: 12px 0;
                `}
              />
              <Typography.Paragraph>
                <Typography.Text strong>content</Typography.Text>{" "}
                <Typography.Text type="secondary">string</Typography.Text>
              </Typography.Paragraph>
              <Typography.Text>
                The contents of the message.{" "}
                <Typography.Text code>content</Typography.Text> is required for
                all messages except assistant messages with function calls.
              </Typography.Text>
            </Card>
          </Card>
        </ThemeProvider>
      </Col>
    </Row>
  );
};
