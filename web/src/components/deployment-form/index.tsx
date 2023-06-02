import { FC, ReactNode, useMemo } from "react";
import { css } from "@emotion/react";
import {
  Button,
  Cascader,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Space,
} from "antd";
import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import dayjs from "dayjs";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";

interface RawForm {
  name: string;
  min_replicas: number;
  accelerator_num?: number;
  accelerator_type?: string;
  cpu: number;
  memory: number;
  photon: string[];
  envs: { name: string; value: string }[];
}

export const DeploymentForm: FC<{
  initialDeploymentValue: Partial<Deployment>;
  submit: (value: Partial<Deployment>) => void;
  buttons: ReactNode;
  deployments: Deployment[];
  photonGroups: PhotonGroup[];
  edit?: boolean;
}> = ({
  initialDeploymentValue,
  deployments,
  submit,
  buttons,
  photonGroups,
  edit = false,
}) => {
  const photon = useMemo(() => {
    const targetMode =
      photonGroups.find((g) => g.id === initialDeploymentValue.photon_id) ||
      photonGroups[0];
    return [targetMode?.id, initialDeploymentValue.photon_id || targetMode?.id];
  }, [initialDeploymentValue.photon_id, photonGroups]);

  const initialValues: Partial<RawForm> = useMemo(() => {
    return {
      name: initialDeploymentValue.name,
      min_replicas: initialDeploymentValue.resource_requirement?.min_replicas,
      accelerator_num:
        initialDeploymentValue.resource_requirement?.accelerator_num,
      accelerator_type:
        initialDeploymentValue.resource_requirement?.accelerator_type,
      cpu: initialDeploymentValue.resource_requirement?.cpu,
      memory: initialDeploymentValue.resource_requirement?.memory,
      photon: photon,
      envs: initialDeploymentValue.envs,
    };
  }, [initialDeploymentValue, photon]);

  const options = photonGroups.map((g) => {
    return {
      value: g.id,
      label: g.name,
      children: g.versions.map((i) => {
        return {
          value: i.id,
          label: dayjs(i.created_at).format("lll"),
        };
      }),
    };
  });
  const transformValue = (value: RawForm): Partial<Deployment> => {
    return {
      name: value.name,
      photon_id: value.photon[value.photon.length - 1],
      resource_requirement: {
        memory: value.memory,
        cpu: value.cpu,
        min_replicas: value.min_replicas,
        accelerator_type: value.accelerator_type,
        accelerator_num: value.accelerator_num,
      },
      envs: value.envs,
    };
  };
  return (
    <Form
      requiredMark={false}
      labelCol={{ span: 7 }}
      wrapperCol={{ span: 14 }}
      initialValues={initialValues}
      onFinish={(e) => submit(transformValue(e))}
      autoComplete="off"
    >
      <Form.Item
        label="Photon"
        name="photon"
        rules={[{ required: true, message: "Please select photon" }]}
      >
        <Cascader showSearch allowClear={false} options={options} />
      </Form.Item>
      <Form.Item
        label="Deployment Name"
        name="name"
        rules={[
          {
            pattern:
              /^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z]([-a-z0-9]*[a-z0-9])?)*$/,
            message: "Deployment name invalid",
          },
          { required: true, message: "Please input deployment name" },
          () => ({
            validator(_, value) {
              if (!deployments.find((d) => d.name === value)) {
                return Promise.resolve();
              } else {
                return Promise.reject(
                  new Error("The name has already been taken")
                );
              }
            },
          }),
        ]}
      >
        <Input disabled={edit} autoFocus placeholder="Deployment name" />
      </Form.Item>
      <Form.Item
        label="Min Replicas"
        name="min_replicas"
        rules={[
          {
            required: true,
            message: "Please input min replicas",
          },
        ]}
      >
        <InputNumber style={{ width: "100%" }} min={0} />
      </Form.Item>
      <Form.Item
        label="CPU"
        name="cpu"
        rules={[
          {
            required: true,
            message: "Please input cpu number",
          },
        ]}
      >
        <InputNumber disabled={edit} style={{ width: "100%" }} min={1} />
      </Form.Item>
      <Form.Item
        label="Memory"
        name="memory"
        rules={[
          {
            required: true,
            message: "Please input memory",
          },
        ]}
      >
        <InputNumber
          disabled={edit}
          style={{ width: "100%" }}
          min={1}
          addonAfter="MB"
        />
      </Form.Item>
      <Form.Item label="Accelerator Type" name="accelerator_type">
        <Input disabled={edit} style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item label="Accelerator Number" name="accelerator_num">
        <InputNumber disabled={edit} style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item label="Environment Variables">
        <Form.List name="envs">
          {(fields, { add, remove }) => (
            <>
              <Row gutter={0}>
                {fields.map(({ key, name, ...restField }) => (
                  <Col key={key} span={24}>
                    <Space
                      css={css`
                        display: flex;
                      `}
                      align="baseline"
                    >
                      <Form.Item
                        wrapperCol={{ span: 24 }}
                        {...restField}
                        name={[name, "name"]}
                        rules={[
                          { required: true, message: "Please input name" },
                        ]}
                      >
                        <Input placeholder="Env name" />
                      </Form.Item>
                      <Form.Item
                        wrapperCol={{ span: 24 }}
                        {...restField}
                        name={[name, "value"]}
                        rules={[
                          { required: true, message: "Please input value" },
                        ]}
                      >
                        <Input placeholder="Env value" />
                      </Form.Item>
                      <MinusCircleOutlined onClick={() => remove(name)} />
                    </Space>
                  </Col>
                ))}
              </Row>

              <Form.Item wrapperCol={{ span: 24 }}>
                <Button
                  type="dashed"
                  onClick={() => add()}
                  block
                  icon={<PlusOutlined />}
                >
                  Add environment variable
                </Button>
              </Form.Item>
            </>
          )}
        </Form.List>
      </Form.Item>
      <Form.Item wrapperCol={{ offset: 7, span: 14 }}>{buttons}</Form.Item>
    </Form>
  );
};
