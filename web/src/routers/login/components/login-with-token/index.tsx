import { FC } from "react";
import { Button, Form, Input } from "antd";
import { useInject } from "@lepton-libs/di";
import { StorageService } from "@lepton-dashboard/services/storage.service";

export const LoginWithToken: FC = () => {
  const storageService = useInject(StorageService);
  const onFinish = (values: { token: string }) => {
    storageService.set(
      StorageService.GLOBAL_SCOPE,
      "CLUSTER_TOKEN",
      values.token
    );
    window.location.replace("/");
  };
  return (
    <Form layout="inline" size="small" onFinish={onFinish}>
      <Form.Item name="token" label="Token" rules={[{ required: true }]}>
        <Input style={{ width: 120 }} type="password" />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit">
          Login
        </Button>
      </Form.Item>
    </Form>
  );
};
