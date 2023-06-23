import { Password } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { FC } from "react";
import { Button, Form, Input } from "antd";
import { useInject } from "@lepton-libs/di";
import { StorageService } from "@lepton-dashboard/services/storage.service";

export const TokenLogin: FC = () => {
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
    <Form layout="horizontal" onFinish={onFinish}>
      <Form.Item name="token" rules={[{ required: true, message: "" }]}>
        <Input
          style={{ width: "100%" }}
          placeholder="Access Token"
          type="password"
          autoFocus
          suffix={<CarbonIcon icon={<Password />} />}
        />
      </Form.Item>
      <Form.Item>
        <Button block type="primary" htmlType="submit">
          Login With Access Token
        </Button>
      </Form.Item>
    </Form>
  );
};
