import { useInject } from "@lepton-libs/di";
import { Button, Form, Input, InputRef } from "antd";
import { FC, useEffect, useMemo, useRef, useState } from "react";
import { ImagePullSecretService } from "@lepton-dashboard/routers/workspace/services/image-pull-secret.service";
import { ImagePullSecret } from "@lepton-dashboard/interfaces/image-pull-secrets";

export const RegistryForm: FC<{
  finish: () => void;
}> = ({ finish }) => {
  const nameRef = useRef<InputRef | null>(null);
  const [loading, setLoading] = useState(false);
  const imagePullSecretService = useInject(ImagePullSecretService);

  useEffect(() => {
    if (nameRef.current) {
      nameRef.current.focus();
    }
  }, []);

  const initialValues: ImagePullSecret = useMemo(() => {
    return {
      metadata: {
        name: "",
      },
      spec: {
        registry_server: "",
        username: "",
        password: "",
        email: "",
      },
    };
  }, []);

  const onFinish = (secret: ImagePullSecret) => {
    imagePullSecretService.createImagePullSecret(secret).subscribe({
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
      preserve={false}
      layout="vertical"
      requiredMark={false}
      initialValues={initialValues}
      onFinish={onFinish}
      autoComplete="off"
    >
      <Form.Item
        label="Name"
        name={["metadata", "name"]}
        rules={[
          { required: true, message: "Please input name" },
          {
            pattern: /^[a-z0-9]([-.]?[a-z0-9])*$/,
            message:
              "Name must consist of lower case alphanumeric characters, '-' or '.', and must start and end with an alphanumeric character.",
          },
        ]}
      >
        <Input ref={nameRef} placeholder="Registry name" />
      </Form.Item>

      <Form.Item
        label="Registry"
        name={["spec", "registry_server"]}
        rules={[{ required: true, message: "Please input registry URL" }]}
      >
        <Input placeholder="E.g. https://index.docker.io" />
      </Form.Item>

      <Form.Item
        label="Username"
        name={["spec", "username"]}
        rules={[{ message: "Please input username" }]}
      >
        <Input placeholder="Username" />
      </Form.Item>

      <Form.Item
        label="Password"
        name={["spec", "password"]}
        rules={[{ message: "Please input password" }]}
      >
        <Input.Password placeholder="Password" />
      </Form.Item>

      <Form.Item
        label="Email"
        name={["spec", "email"]}
        rules={[{ message: "Please input email" }]}
      >
        <Input placeholder="Email" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={loading}>
        Submit
      </Button>
    </Form>
  );
};
