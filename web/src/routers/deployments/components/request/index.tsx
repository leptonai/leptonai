import { FC, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { css } from "@emotion/react";
import { Button, Form, Input } from "antd";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";

export const Request: FC<{ url: string }> = ({ url }) => {
  const deploymentService = useInject(DeploymentService);
  const [result, setResult] = useState("");
  const request = (value: string) => {
    setLoading(true);
    deploymentService.request(url, value).subscribe({
      next: (data) => {
        setResult(JSON.stringify(data));
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    });
  };
  const [loading, setLoading] = useState(false);
  return (
    <Card title="Request Endpoint">
      <Form
        css={css`
          margin-top: 12px;
        `}
        requiredMark={false}
        onFinish={(v) => request(v.request)}
        autoComplete="off"
      >
        <Form.Item name="request">
          <Input.TextArea />
        </Form.Item>
        <Form.Item>
          <Button loading={loading} type="primary" htmlType="submit">
            Submit
          </Button>
        </Form.Item>
      </Form>
      <pre
        css={css`
          margin-top: 12px;
          white-space: pre-wrap;
        `}
      >
        {result}
      </pre>
    </Card>
  );
};
