import { FC, ReactNode, useMemo, useState } from "react";
import { css } from "@emotion/react";
import {
  Button,
  Cascader,
  Checkbox,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
} from "antd";
import { MinusOutlined, PlusOutlined } from "@ant-design/icons";

import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import dayjs from "dayjs";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { useInject } from "@lepton-libs/di";
import { Rule } from "rc-field-form/lib/interface";
import { WorkspaceTrackerService } from "../../services/workspace-tracker.service";

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
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const clusterInfo = workspaceTrackerService.cluster!.data;
  const [form] = Form.useForm();
  const [enableAccelerator, setEnableAccelerator] = useState(
    !!initialDeploymentValue.resource_requirement?.accelerator_num
  );
  const supportedAccelerators = Object.keys(
    clusterInfo.supported_accelerators
  ).map((i) => ({ label: i, value: i }));

  const initialMax = initialDeploymentValue.resource_requirement
    ?.accelerator_type
    ? clusterInfo.supported_accelerators[
        initialDeploymentValue.resource_requirement?.accelerator_type
      ] || 0
    : 0;

  const [maxAcceleratorCount, setMaxAcceleratorCount] = useState(initialMax);

  const acceleratorCountRules: Rule[] = useMemo(() => {
    return [
      {
        max: maxAcceleratorCount,
        type: "number",
        message: `The accelerator available is ${maxAcceleratorCount}`,
      },
      {
        required: true,
        message: `Please input the accelerator number`,
      },
    ];
  }, [maxAcceleratorCount]);
  const photon = useMemo(() => {
    const latest =
      photonGroups.find((g) =>
        g.versions.some((v) => v.id === initialDeploymentValue.photon_id)
      ) || photonGroups[0];

    return [latest?.id, initialDeploymentValue.photon_id || latest?.id];
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
      enable_accelerator:
        !!initialDeploymentValue.resource_requirement?.accelerator_num,
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
        accelerator_type: enableAccelerator ? value.accelerator_type : "",
        accelerator_num: enableAccelerator ? value.accelerator_num : 0,
      },
      envs: value.envs,
    };
  };
  return (
    <Form
      form={form}
      onValuesChange={() => {
        const acceleratorType = form.getFieldValue(["accelerator_type"]);
        if (acceleratorType) {
          setMaxAcceleratorCount(
            clusterInfo.supported_accelerators[acceleratorType]
          );
        } else {
          setMaxAcceleratorCount(0);
        }
        void form.validateFields(["accelerator_num"]);
      }}
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
            max: 32,
            type: "string",
            message: "Exceeded maximum length",
          },
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
            max: clusterInfo.max_generic_compute_size.Core,
            type: "number",
            message: `The maximum available core is ${clusterInfo.max_generic_compute_size.Core}`,
          },
          {
            required: true,
            message: "Please input cpu number",
          },
        ]}
      >
        <InputNumber
          disabled={edit}
          style={{ width: "100%" }}
          min={1}
          max={clusterInfo.max_generic_compute_size.Core}
        />
      </Form.Item>
      <Form.Item
        label="Memory"
        name="memory"
        rules={[
          {
            max: clusterInfo.max_generic_compute_size.Memory,
            type: "number",
            message: `The maximum available memory is ${clusterInfo.max_generic_compute_size.Memory} MB`,
          },
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
          max={clusterInfo.max_generic_compute_size.Memory}
          addonAfter="MB"
        />
      </Form.Item>
      <Form.Item
        css={css`
          margin-bottom: 0;
        `}
        label="Environment Variables"
      >
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
                        <Input disabled={edit} placeholder="Env name" />
                      </Form.Item>
                      <Form.Item
                        wrapperCol={{ span: 24 }}
                        {...restField}
                        name={[name, "value"]}
                        rules={[
                          { required: true, message: "Please input value" },
                        ]}
                      >
                        <Input disabled={edit} placeholder="Env value" />
                      </Form.Item>
                      <Button disabled={edit} onClick={() => remove(name)}>
                        <MinusOutlined />
                      </Button>
                    </Space>
                  </Col>
                ))}
              </Row>

              <Form.Item wrapperCol={{ span: 24 }}>
                <Button
                  type="dashed"
                  disabled={edit}
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
      <Form.Item wrapperCol={{ offset: 7, span: 14 }}>
        <Checkbox
          disabled={edit}
          value={enableAccelerator}
          onChange={(e) => setEnableAccelerator(e.target.checked)}
        >
          Enable Accelerator
        </Checkbox>
      </Form.Item>
      {enableAccelerator && (
        <>
          <Form.Item
            rules={[
              {
                required: true,
                message: `Please input the accelerator type`,
              },
            ]}
            label="Accelerator Type"
            name="accelerator_type"
          >
            <Select
              disabled={edit}
              notFoundContent={
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="No accelerator aviailable"
                />
              }
              placeholder="Input accelerator type"
              options={supportedAccelerators}
              showSearch
            />
          </Form.Item>
          <Form.Item
            rules={acceleratorCountRules}
            label="Accelerator Number"
            name="accelerator_num"
          >
            <InputNumber
              placeholder="Input accelerator number"
              min={0}
              disabled={edit}
              style={{ width: "100%" }}
            />
          </Form.Item>
        </>
      )}

      <Form.Item wrapperCol={{ offset: 7, span: 14 }}>{buttons}</Form.Item>
    </Form>
  );
};
