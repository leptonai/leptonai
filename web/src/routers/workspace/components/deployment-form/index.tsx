import { Asterisk, Hashtag } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FormListOperation } from "antd/es/form/FormList";
import { FC, ReactNode, useMemo, useRef, useState } from "react";
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

import {
  Deployment,
  DeploymentEnv,
  DeploymentSecretEnv,
} from "@lepton-dashboard/interfaces/deployment";
import dayjs from "dayjs";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { useInject } from "@lepton-libs/di";
import { Rule } from "rc-field-form/lib/interface";
import { map } from "rxjs";
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
  secret_envs: { name: string; value: string }[];
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
  const addSecretFnRef = useRef<FormListOperation["add"] | null>(null);
  const addVariableFnRef = useRef<FormListOperation["add"] | null>(null);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const secretService = useInject(SecretService);
  const clusterInfo = workspaceTrackerService.cluster!.data;
  const secretOptions = useStateFromObservable(
    () =>
      secretService.listSecrets().pipe(
        map((secrets) => {
          return secrets.map((s) => ({ label: s.name, value: s.name }));
        })
      ),
    []
  );
  const [form] = Form.useForm();
  const [enableAccelerator, setEnableAccelerator] = useState(
    edit
      ? !!initialDeploymentValue.resource_requirement?.accelerator_num
      : false
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
      envs: initialDeploymentValue.envs?.filter(
        (e): e is DeploymentEnv => !!(e as DeploymentEnv).value
      ),
      secret_envs: initialDeploymentValue.envs
        ?.filter(
          (e): e is DeploymentSecretEnv =>
            !!(e as DeploymentSecretEnv).value_from.secret_name_ref
        )
        .map((e) => {
          return {
            name: e.name,
            value: e.value_from.secret_name_ref,
          };
        }),
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
      envs: [
        ...(value.envs || []),
        ...(value.secret_envs || []).map((e) => {
          return {
            name: e.name,
            value_from: {
              secret_name_ref: e.value,
            },
          };
        }),
      ],
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
        label="Replicas"
        name="min_replicas"
        rules={[
          {
            required: true,
            message: "Please input replicas",
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
            max: clusterInfo.max_generic_compute_size.core,
            type: "number",
            message: `The maximum available core is ${clusterInfo.max_generic_compute_size.core}`,
          },
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
            max: clusterInfo.max_generic_compute_size.memory,
            type: "number",
            message: `The maximum available memory is ${clusterInfo.max_generic_compute_size.memory} MB`,
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
          {(fields, { add, remove }) => {
            addVariableFnRef.current = add;
            return (
              <Row gutter={0}>
                {fields.map(({ key, name, ...restField }) => (
                  <Col key={`${name}-${key}`} span={24}>
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
                        <Input
                          autoFocus
                          disabled={edit}
                          placeholder="Variable name"
                        />
                      </Form.Item>
                      <Form.Item
                        css={css`
                          margin-bottom: 0;
                        `}
                        wrapperCol={{ span: 24 }}
                      >
                        <Space.Compact block>
                          <Button
                            disabled
                            icon={<CarbonIcon icon={<Hashtag />} />}
                          />
                          <Form.Item
                            {...restField}
                            name={[name, "value"]}
                            rules={[
                              { required: true, message: "Please input value" },
                            ]}
                          >
                            <Input
                              disabled={edit}
                              placeholder="Variable value"
                            />
                          </Form.Item>
                        </Space.Compact>
                      </Form.Item>
                      <Button disabled={edit} onClick={() => remove(name)}>
                        <MinusOutlined />
                      </Button>
                    </Space>
                  </Col>
                ))}
              </Row>
            );
          }}
        </Form.List>
        <Form.List name="secret_envs">
          {(fields, { add, remove }) => {
            addSecretFnRef.current = add;
            return (
              <Row gutter={0}>
                {fields.map(({ key, name, ...restField }) => (
                  <Col key={`${name}-${key}`} span={24}>
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
                        <Input
                          autoFocus
                          disabled={edit}
                          placeholder="Variable name"
                        />
                      </Form.Item>
                      <Form.Item
                        css={css`
                          margin-bottom: 0;
                        `}
                        wrapperCol={{ span: 24 }}
                      >
                        <Space.Compact block>
                          <Button
                            disabled
                            icon={<CarbonIcon icon={<Asterisk />} />}
                          />
                          <Form.Item
                            {...restField}
                            name={[name, "value"]}
                            rules={[
                              { required: true, message: "Please input value" },
                            ]}
                          >
                            <Select
                              disabled={edit}
                              placeholder="Secret"
                              style={{ width: "152px" }}
                              options={secretOptions}
                            />
                          </Form.Item>
                        </Space.Compact>
                      </Form.Item>
                      <Button disabled={edit} onClick={() => remove(name)}>
                        <MinusOutlined />
                      </Button>
                    </Space>
                  </Col>
                ))}
              </Row>
            );
          }}
        </Form.List>
        <Form.Item wrapperCol={{ span: 24 }}>
          <Space.Compact block>
            <Button
              disabled={edit}
              block
              onClick={() =>
                addVariableFnRef.current && addVariableFnRef.current()
              }
              icon={<PlusOutlined />}
            >
              Add variable
            </Button>
            <Button
              disabled={edit}
              block
              onClick={() => addSecretFnRef.current && addSecretFnRef.current()}
              icon={<PlusOutlined />}
            >
              Add secret
            </Button>
          </Space.Compact>
        </Form.Item>
      </Form.Item>

      <Form.Item
        wrapperCol={{
          xs: { offset: 0, span: 24 },
          sm: { offset: 7, span: 14 },
        }}
      >
        <Checkbox
          disabled={edit}
          checked={enableAccelerator}
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

      <Form.Item
        wrapperCol={{
          xs: { offset: 0, span: 24 },
          sm: { offset: 7, span: 14 },
        }}
      >
        {buttons}
      </Form.Item>
    </Form>
  );
};
