import { Secret } from "@lepton-dashboard/interfaces/secret";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { useInject } from "@lepton-libs/di";
import { Button, Form, Input, InputRef } from "antd";
import { FC, useEffect, useRef, useState } from "react";

export const SecretForm: FC<{
  finish: () => void;
  initialValues?: Secret;
  edit?: boolean;
}> = ({ finish, initialValues, edit }) => {
  const nameRef = useRef<InputRef | null>(null);
  const valueRef = useRef<InputRef | null>(null);
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

  useEffect(() => {
    if (edit && valueRef.current) {
      valueRef.current.focus();
    } else if (nameRef.current) {
      nameRef.current.focus();
    }
  }, [edit]);

  return (
    <Form
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
        rules={[
          { required: true, message: "Please input name" },
          {
            pattern: /^((?!LEPTON_).)*$/,
            message: "Secret name cannot start with reserved prefix",
          },
        ]}
      >
        <Input ref={nameRef} disabled={edit} placeholder="Secret name" />
      </Form.Item>

      <Form.Item
        label="Value"
        name="value"
        rules={[{ required: true, message: "Please input value" }]}
      >
        <Input ref={valueRef} placeholder="Secret value" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={loading}>
        Submit
      </Button>
    </Form>
  );
};
