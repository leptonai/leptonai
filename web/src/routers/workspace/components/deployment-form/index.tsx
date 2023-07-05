import { Asterisk, Hashtag, Launch, TrashCan } from "@carbon/icons-react";
import { IconContainer } from "@lepton-dashboard/components/icon-container";
import { CarbonIcon, EqualIcon } from "@lepton-dashboard/components/icons";
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
  Collapse,
  Dropdown,
  Empty,
  Form,
  Input,
  InputNumber,
  MenuProps,
  Row,
  Select,
  Space,
} from "antd";
import { DownOutlined, PlusOutlined } from "@ant-design/icons";

import {
  Deployment,
  DeploymentEnv,
  DeploymentMount,
  DeploymentSecretEnv,
} from "@lepton-dashboard/interfaces/deployment";
import dayjs from "dayjs";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { useInject } from "@lepton-libs/di";
import { Rule } from "rc-field-form/lib/interface";
import { useNavigate } from "react-router-dom";
import { WorkspaceTrackerService } from "../../services/workspace-tracker.service";
import { StorageSelect } from "@lepton-dashboard/routers/workspace/components/storage-select";

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
  mounts: DeploymentMount[];
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
  const navigate = useNavigate();
  const addSecretFnRef = useRef<FormListOperation["add"] | null>(null);
  const addVariableFnRef = useRef<FormListOperation["add"] | null>(null);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const secretService = useInject(SecretService);
  const workspaceDetail = workspaceTrackerService.workspace!.data;
  const secrets = useStateFromObservable(() => secretService.listSecrets(), []);
  const secretOptions = useMemo(() => {
    return secrets.map((s) => ({ label: s.name, value: s.name }));
  }, [secrets]);
  const secretMenus: MenuProps["items"] = useMemo(() => {
    let menus: MenuProps["items"] = [];
    if (secrets.length > 0) {
      menus = secrets.map((s) => ({
        label: (
          <>
            Add secret <strong>{s.name}</strong>
          </>
        ),
        key: s.name,
        icon: <Asterisk />,
        onClick: (v: { key: string }) => {
          addSecretFnRef.current?.({ name: v.key, value: v.key });
        },
      }));
    } else {
      menus = [
        {
          label: "No secret found, create one",
          icon: <Launch />,
          key: "create_new_secret",
          onClick: () => {
            navigate(
              `/workspace/${workspaceTrackerService.name}/settings/secrets`,
              {
                relative: "route",
              }
            );
          },
        },
      ];
    }
    menus.unshift({
      label: "Add variable",
      key: "Add variable",
      icon: <Hashtag />,
      onClick: () => {
        addVariableFnRef.current && addVariableFnRef.current();
      },
    });
    return menus;
  }, [navigate, secrets, workspaceTrackerService.name]);
  const [form] = Form.useForm();
  const [enableAccelerator, setEnableAccelerator] = useState(
    edit
      ? !!initialDeploymentValue.resource_requirement?.accelerator_num
      : false
  );
  const supportedAccelerators = Object.keys(
    workspaceDetail.supported_accelerators
  ).map((i) => ({ label: i, value: i }));

  const initialMax = initialDeploymentValue.resource_requirement
    ?.accelerator_type
    ? workspaceDetail.supported_accelerators[
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
      mounts: initialDeploymentValue.mounts || [],
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
      mounts: (value.mounts || [])
        .map((m) => {
          return {
            path: m.path?.trim(),
            mount_path: m.mount_path?.trim(),
          };
        })
        .filter((m) => m.path && m.mount_path),
    };
  };
  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={() => {
        const acceleratorType = form.getFieldValue(["accelerator_type"]);
        if (acceleratorType) {
          setMaxAcceleratorCount(
            workspaceDetail.supported_accelerators[acceleratorType]
          );
        } else {
          setMaxAcceleratorCount(0);
        }
        void form.validateFields(["accelerator_num"]);
      }}
      requiredMark={false}
      initialValues={initialValues}
      onFinish={(e) => submit(transformValue(e))}
      autoComplete="off"
    >
      <Form.Item
        label="Name"
        name="name"
        rules={[
          {
            max: 32,
            type: "string",
            message: "Exceeded maximum length",
          },
          {
            pattern:
              /^[a-z]([-a-z0-9]*[a-z0-9])?(\.[a-z]([-a-z0-9]*[a-z0-9])?)*$/,
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
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="Photon"
            name="photon"
            rules={[{ required: true, message: "Please select photon" }]}
          >
            <Cascader showSearch allowClear={false} options={options} />
          </Form.Item>
        </Col>
        <Col span={12}>
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
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="CPU"
            name="cpu"
            rules={[
              {
                max: workspaceDetail.max_generic_compute_size.core,
                type: "number",
                message: `The maximum available core is ${workspaceDetail.max_generic_compute_size.core}`,
              },
              {
                required: true,
                message: "Please input cpu number",
              },
            ]}
          >
            <InputNumber disabled={edit} style={{ width: "100%" }} min={1} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Memory"
            name="memory"
            rules={[
              {
                max: workspaceDetail.max_generic_compute_size.memory,
                type: "number",
                message: `The maximum available memory is ${workspaceDetail.max_generic_compute_size.memory} MB`,
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
        </Col>
      </Row>
      <Form.Item>
        <Checkbox
          disabled={edit}
          checked={enableAccelerator}
          onChange={(e) => setEnableAccelerator(e.target.checked)}
        >
          Enable Accelerator
        </Checkbox>
      </Form.Item>
      {enableAccelerator && (
        <Row gutter={16}>
          <Col span={12}>
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
          </Col>
          <Col span={12}>
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
          </Col>
        </Row>
      )}
      <Collapse
        css={css`
          margin-bottom: 24px;
        `}
        size="small"
        items={[
          {
            label: "Advanced Settings",
            key: "Advanced",
            children: (
              <div
                css={css`
                  padding-top: 12px;
                `}
              >
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
                              <Row gutter={8} wrap={false}>
                                <Col flex="1 1 auto">
                                  <Form.Item
                                    {...restField}
                                    name={[name, "name"]}
                                    rules={[
                                      {
                                        required: true,
                                        message: "Please input name",
                                      },
                                    ]}
                                  >
                                    <Input
                                      autoFocus
                                      disabled={edit}
                                      placeholder="Variable name"
                                    />
                                  </Form.Item>
                                </Col>
                                <Col flex={0}>
                                  <IconContainer>
                                    <EqualIcon />
                                  </IconContainer>
                                </Col>
                                <Col flex="1 1 300px">
                                  <Space.Compact block>
                                    <Button
                                      disabled
                                      icon={<CarbonIcon icon={<Hashtag />} />}
                                    />
                                    <Form.Item
                                      css={css`
                                        flex: 1;
                                      `}
                                      {...restField}
                                      name={[name, "value"]}
                                      rules={[
                                        {
                                          required: true,
                                          message: "Please input value",
                                        },
                                      ]}
                                    >
                                      <Input
                                        disabled={edit}
                                        placeholder="Variable value"
                                      />
                                    </Form.Item>
                                  </Space.Compact>
                                </Col>
                                <Col flex={0}>
                                  <Button
                                    icon={<CarbonIcon icon={<TrashCan />} />}
                                    disabled={edit}
                                    onClick={() => remove(name)}
                                  />
                                </Col>
                              </Row>
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
                              <Row gutter={8} wrap={false}>
                                <Col flex="1 1 auto">
                                  <Form.Item
                                    {...restField}
                                    name={[name, "name"]}
                                    rules={[
                                      {
                                        required: true,
                                        message: "Please input name",
                                      },
                                    ]}
                                  >
                                    <Input
                                      autoFocus
                                      disabled={edit}
                                      placeholder="Variable name"
                                    />
                                  </Form.Item>
                                </Col>
                                <Col flex={0}>
                                  <IconContainer>
                                    <EqualIcon />
                                  </IconContainer>
                                </Col>
                                <Col flex="1 1 300px">
                                  <Space.Compact block>
                                    <Button
                                      disabled
                                      icon={<CarbonIcon icon={<Asterisk />} />}
                                    />
                                    <Form.Item
                                      css={css`
                                        flex: 1;
                                      `}
                                      {...restField}
                                      name={[name, "value"]}
                                      rules={[
                                        {
                                          required: true,
                                          message: "Please input value",
                                        },
                                      ]}
                                    >
                                      <Select
                                        disabled={edit}
                                        style={{ width: "100%" }}
                                        placeholder="Secret"
                                        showArrow={false}
                                        options={secretOptions}
                                      />
                                    </Form.Item>
                                  </Space.Compact>
                                </Col>
                                <Col flex={0}>
                                  <Button
                                    icon={<CarbonIcon icon={<TrashCan />} />}
                                    disabled={edit}
                                    onClick={() => remove(name)}
                                  />
                                </Col>
                              </Row>
                            </Col>
                          ))}
                        </Row>
                      );
                    }}
                  </Form.List>
                  <Form.Item wrapperCol={{ span: 24 }}>
                    <Dropdown
                      disabled={edit}
                      menu={{ items: secretMenus }}
                      trigger={["click"]}
                    >
                      <Button disabled={edit} block>
                        <Space>
                          <PlusOutlined />
                          Add variable / secret
                          <DownOutlined />
                        </Space>
                      </Button>
                    </Dropdown>
                  </Form.Item>
                </Form.Item>
                <Form.Item
                  css={css`
                    margin-bottom: 0;
                  `}
                  label="Storage Mounts"
                >
                  <Form.List name="mounts">
                    {(fields, { add, remove }) => {
                      return (
                        <>
                          {fields.map((field, index) => (
                            <Row gutter={8} key={`mounts-${index}`}>
                              <Col flex="1 1 auto">
                                <Form.Item
                                  {...field}
                                  initialValue=""
                                  name={[field.name, "mount_path"]}
                                  key={`mounts-${index}-mount_path`}
                                  rules={[
                                    {
                                      required: true,
                                      message: "Missing mount path",
                                    },
                                  ]}
                                >
                                  <Input disabled={edit} placeholder="mount" />
                                </Form.Item>
                              </Col>
                              <Col flex={0}>
                                <IconContainer>
                                  <EqualIcon />
                                </IconContainer>
                              </Col>
                              <Col flex="1 1 300px">
                                <Form.Item
                                  {...field}
                                  initialValue=""
                                  name={[field.name, "path"]}
                                  key={`mounts-${index}-path`}
                                  rules={[
                                    {
                                      required: true,
                                      message: "Missing storage path",
                                    },
                                  ]}
                                >
                                  <StorageSelect
                                    disabled={edit}
                                    placeholder="from storage"
                                  />
                                </Form.Item>
                              </Col>
                              <Col flex={0}>
                                <Button
                                  type="default"
                                  disabled={edit}
                                  icon={<CarbonIcon icon={<TrashCan />} />}
                                  onClick={() => remove(index)}
                                />
                              </Col>
                            </Row>
                          ))}
                          <Form.Item>
                            <Button
                              block
                              disabled={edit}
                              icon={<PlusOutlined />}
                              onClick={add}
                            >
                              Add storage mount
                            </Button>
                          </Form.Item>
                        </>
                      );
                    }}
                  </Form.List>
                </Form.Item>
              </div>
            ),
          },
        ]}
      />

      <Form.Item>{buttons}</Form.Item>
    </Form>
  );
};
