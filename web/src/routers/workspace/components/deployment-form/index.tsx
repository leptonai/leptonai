import {
  ArrowRight,
  Asterisk,
  Hashtag,
  Launch,
  TrashCan,
} from "@carbon/icons-react";
import { IconContainer } from "@lepton-dashboard/components/icon-container";
import { CarbonIcon, EqualIcon } from "@lepton-dashboard/components/icons";
import { PhotonLabel } from "@lepton-dashboard/routers/workspace/components/photon-label";
import { ResourceShape } from "@lepton-dashboard/routers/workspace/components/resource-shape";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FormListOperation } from "antd/es/form/FormList";
import { FC, ReactNode, useMemo, useRef } from "react";
import { css } from "@emotion/react";
import {
  Button,
  Cascader,
  Checkbox,
  Col,
  Collapse,
  Dropdown,
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
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon";
import { useInject } from "@lepton-libs/di";
import { StorageSelect } from "@lepton-dashboard/routers/workspace/components/storage-select";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

interface RawForm {
  name: string;
  min_replicas: number;
  shape?: string;
  photon: string[];
  enable_public: boolean;
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
  const navigateService = useInject(NavigateService);
  const addSecretFnRef = useRef<FormListOperation["add"] | null>(null);
  const addVariableFnRef = useRef<FormListOperation["add"] | null>(null);
  const secretService = useInject(SecretService);
  const hardwareService = useInject(HardwareService);
  const shapeOptions = hardwareService.shapes.map((i) => ({
    label: <ResourceShape shape={i} />,
    optionLabelProp: hardwareService.hardwareShapes[i].DisplayName,
    value: i,
  }));
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
            navigateService.navigateTo("settingsSecrets", null, {
              relative: "route",
            });
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
  }, [navigateService, secrets]);
  const [form] = Form.useForm();
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
      photon: photon,
      enable_public: !initialDeploymentValue.api_tokens?.length,
      shape: initialDeploymentValue.resource_requirement?.resource_shape,
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
          label: (
            <PhotonLabel
              showTime
              showName={false}
              name={g.name}
              id={i.id}
              created_at={i.created_at}
            />
          ),
        };
      }),
    };
  });
  const transformValue = (value: RawForm): Partial<Deployment> => {
    return {
      name: value.name,
      photon_id: value.photon[value.photon.length - 1],
      resource_requirement: {
        min_replicas: value.min_replicas,
        resource_shape: value.shape,
      },
      api_tokens: value.enable_public
        ? []
        : [{ value_from: { token_name_ref: "WORKSPACE_TOKEN" } }],
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
            message:
              "Only alphanumeric characters (a-z, 0-9) and '-' allowed here",
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
        <Col span={16}>
          <Form.Item
            label="Photon"
            name="photon"
            rules={[{ required: true, message: "Please select photon" }]}
          >
            <Cascader showSearch allowClear={false} options={options} />
          </Form.Item>
        </Col>
        <Col span={8}>
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
            <InputNumber
              style={{ width: "100%" }}
              min={1}
              precision={0}
              step={1}
            />
          </Form.Item>
        </Col>
      </Row>
      <Form.Item
        label="Resource type"
        name="shape"
        rules={[{ required: true }]}
      >
        <Select disabled={edit} options={shapeOptions} />
      </Form.Item>
      <Form.Item name="enable_public" valuePropName="checked">
        <Checkbox disabled={edit}>Enable public access</Checkbox>
      </Form.Item>
      <Collapse
        css={css`
          margin-bottom: 24px;
        `}
        size="small"
        items={[
          {
            label: "Advanced settings",
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
                  label="Environment variables"
                >
                  <Form.List name="envs">
                    {(fields, { add, remove }) => {
                      addVariableFnRef.current = add;
                      return (
                        <Row gutter={0}>
                          {fields.map(({ key, name, ...restField }) => (
                            <Col key={`${name}-${key}`} span={24}>
                              <Row gutter={8} wrap={false}>
                                <Col flex="1 1 180px">
                                  <Form.Item
                                    {...restField}
                                    name={[name, "name"]}
                                    rules={[
                                      {
                                        required: true,
                                        message: "Please input name",
                                      },
                                      {
                                        pattern: /^((?!LEPTON_).)*$/,
                                        message:
                                          "Environment variable name cannot start with reserved prefix",
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
                                <Col flex="1 1 280px">
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
                                <Col flex="1 1 180px">
                                  <Form.Item
                                    {...restField}
                                    name={[name, "name"]}
                                    rules={[
                                      {
                                        required: true,
                                        message: "Please input name",
                                      },
                                      {
                                        pattern: /^((?!LEPTON_).)*$/,
                                        message:
                                          "Secret name cannot start with reserved prefix",
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
                                <Col flex="1 1 280px">
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
                  label="Mount files from storage to the deployment"
                >
                  <Form.List name="mounts">
                    {(fields, { add, remove }) => {
                      return (
                        <>
                          {fields.map((field, index) => (
                            <Row
                              gutter={8}
                              key={`mounts-${index}`}
                              wrap={false}
                            >
                              <Col flex="1 1 180px">
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
                                    placeholder="storage"
                                  />
                                </Form.Item>
                              </Col>
                              <Col flex={0}>
                                <IconContainer>
                                  <CarbonIcon icon={<ArrowRight />} />
                                </IconContainer>
                              </Col>
                              <Col flex="1 1 280px">
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

      <Form.Item noStyle>
        <div>{buttons}</div>
      </Form.Item>
    </Form>
  );
};
