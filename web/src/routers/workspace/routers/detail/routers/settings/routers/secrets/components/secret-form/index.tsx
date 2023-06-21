import { css } from "@emotion/react";
import { Secret } from "@lepton-dashboard/interfaces/secret";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { useInject } from "@lepton-libs/di";
import { Button, Form, Input } from "antd";
import { FC, useState } from "react";

export const SecretForm: FC<{
  finish: () => void;
  initialValues?: Secret;
  edit?: boolean;
}> = ({ finish, initialValues, edit }) => {
  const [loading, setLoading] = useState(false);
  const secretService = useInject(SecretService);
  const onFinish = (secret: Secret) => {
    secretService.createOrUpdateSecret(secret).subscribe({
      next: () => {
        setLoading(false);
        finish();
      },
      error: () => {
        setLoading(false);
      },
    });
  };

  return (
    <Form
      css={css`
        padding: 8px 0;
      `}
      preserve={false}
      layout="vertical"
      requiredMark={false}
      onFinish={onFinish}
      initialValues={initialValues}
      autoComplete="off"
    >
      <Form.Item
        label="Name"
        name="name"
        rules={[{ required: true, message: "Please input name" }]}
      >
        <Input disabled={edit} placeholder="Secret name" />
      </Form.Item>

      <Form.Item
        label="Value"
        name="value"
        rules={[{ required: true, message: "Please input value" }]}
      >
        <Input placeholder="Secret value" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={loading}>
        Submit
      </Button>
    </Form>
  );
};
