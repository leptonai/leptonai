import { CloudUpload } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { Card } from "@lepton-dashboard/components/card";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import {
  App,
  Button,
  Col,
  Divider,
  Form,
  Input,
  InputRef,
  Popover,
  Row,
  Spin,
  Typography,
  Upload as AntdUpload,
} from "antd";
import { FC, useCallback, useEffect, useRef, useState } from "react";
import type { UploadChangeParam } from "antd/es/upload";

export interface CreateProps {
  finish: () => void;
}

interface FormData {
  fileList: [{ originFileObj: File }];
  name: string;
}

const normFile = (e: UploadChangeParam<unknown>) => {
  if (Array.isArray(e)) {
    return e;
  }
  return e?.fileList;
};

const limit4MB = 4 * 1024 * 1024;

export const CreateJob: FC<CreateProps> = ({ finish = () => void 0 }) => {
  const fineTuneService = useInject(TunaService);
  const refreshService = useInject(RefreshService);
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<InputRef | null>(null);
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);
  const submit = useCallback(
    (formData?: FormData) => {
      if (!formData) {
        return;
      }
      const {
        fileList: [{ originFileObj: file }],
        name,
      } = formData;
      setLoading(true);
      fineTuneService.addJob(name, file).subscribe({
        next: () => {
          finish();
          setLoading(false);
          refreshService.refresh();
          void message.success("Create training job successfully");
        },
        error: () => {
          setLoading(false);
        },
      });
    },
    [fineTuneService, finish, message, refreshService]
  );

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Form
          form={form}
          onFinish={submit}
          layout="vertical"
          requiredMark={false}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[
              { required: true, message: "Please enter tuna name" },
              { type: "string", max: 32 },
              {
                pattern: /^[a-z]([-a-z0-9]*[a-z0-9])?$/,
                message:
                  "Name must be lowercase alphanumeric characters or '-', and must start with an alphabetical character and end with a alphanumeric character",
              },
            ]}
          >
            <Input readOnly={loading} ref={inputRef} placeholder="Tuna name" />
          </Form.Item>
          <Form.Item
            label="Training data"
            required
            css={css`
              margin-bottom: 0;
            `}
          >
            <Popover
              placement="right"
              content={
                <ThemeProvider token={{ fontSize: 12, padding: 4 }}>
                  <Typography.Text strong>Data JSON format</Typography.Text>
                  <Typography.Paragraph>
                    <Typography.Text strong>messages</Typography.Text>{" "}
                    <Typography.Text type="secondary">array</Typography.Text>
                  </Typography.Paragraph>
                  <Typography.Text>
                    A list of messages comprising the conversation so far.
                  </Typography.Text>
                  <Card
                    paddingless
                    css={css`
                      margin-top: 16px;
                      padding: 8px;
                    `}
                  >
                    <Typography.Paragraph>
                      <Typography.Text strong>role</Typography.Text>{" "}
                      <Typography.Text type="secondary">string</Typography.Text>
                    </Typography.Paragraph>
                    <Typography.Text>
                      The role of the messages author. One of{" "}
                      <Typography.Text code>system</Typography.Text>,{" "}
                      <Typography.Text code>user</Typography.Text>,{" "}
                      <Typography.Text code>assistant</Typography.Text>.
                    </Typography.Text>
                    <Divider
                      css={css`
                        margin: 16px 0;
                      `}
                    />
                    <Typography.Paragraph>
                      <Typography.Text strong>content</Typography.Text>{" "}
                      <Typography.Text type="secondary">string</Typography.Text>
                    </Typography.Paragraph>
                    <Typography.Text>
                      The contents of the message.{" "}
                      <Typography.Text code>content</Typography.Text> is
                      required for all messages.
                    </Typography.Text>
                  </Card>
                </ThemeProvider>
              }
            >
              <Spin spinning={loading}>
                <Form.Item
                  name="fileList"
                  valuePropName="fileList"
                  getValueFromEvent={normFile}
                  rules={[
                    {
                      type: "array",
                      validator: async (_, fileList) => {
                        if (!fileList || fileList.length === 0) {
                          return Promise.reject(
                            new Error("Please upload training data")
                          );
                        }
                        return Promise.resolve();
                      },
                    },
                    {
                      validator: async (_, fileList) => {
                        if (
                          fileList &&
                          fileList[0].originFileObj.size > limit4MB
                        ) {
                          return Promise.reject(
                            new Error(
                              `File size must be less than 4MB, but got ${(
                                fileList[0].originFileObj.size /
                                1024 /
                                1024
                              ).toFixed(2)}MB`
                            )
                          );
                        } else {
                          return Promise.resolve();
                        }
                      },
                    },
                    {
                      warningOnly: true,
                      message: (
                        <Typography.Text type="secondary">
                          If your datasize is bigger than 4 MBs, please reach{" "}
                          out to{" "}
                          <Typography.Link href="mailto:info@lepton.ai">
                            info@lepton.ai
                          </Typography.Link>
                        </Typography.Text>
                      ),
                      validator: async (_, fileList) => {
                        if (
                          fileList &&
                          fileList[0].originFileObj.size > limit4MB
                        ) {
                          return Promise.reject();
                        } else {
                          return Promise.resolve();
                        }
                      },
                    },
                  ]}
                  noStyle
                >
                  <AntdUpload.Dragger
                    disabled={loading}
                    maxCount={1}
                    beforeUpload={() => false}
                    accept="application/JSON, application/json, .json"
                  >
                    <p className="ant-upload-drag-icon">
                      <CarbonIcon icon={<CloudUpload />} />
                    </p>
                    <p className="ant-upload-text">
                      Click or drag to this area to upload training data.
                    </p>
                  </AntdUpload.Dragger>
                </Form.Item>
              </Spin>
            </Popover>
          </Form.Item>
        </Form>
      </Col>
      <Col span={24}>
        <Button
          loading={loading}
          type="primary"
          disabled={loading}
          onClick={() => form.submit()}
        >
          Create
        </Button>
      </Col>
    </Row>
  );
};
