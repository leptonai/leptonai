import { FC, useMemo, useState } from "react";
import {
  App,
  Button,
  Cascader,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
} from "antd";
import { css } from "@emotion/react";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import dayjs from "dayjs";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { PlusOutlined } from "@ant-design/icons";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";

interface RawForm {
  name: string;
  min_replicas: number;
  accelerator_num?: number;
  accelerator_type?: string;
  cpu: number;
  memory: number;
  photon: string[];
}

const CreateDeploymentDetail: FC<{ finish: () => void; photonId?: string }> = ({
  finish,
  photonId,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
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
  const initPhoton = useMemo(() => {
    const targetMode =
      photonGroups.find((g) => g.id === photonId) || photonGroups[0];
    return [targetMode?.id, photonId || targetMode?.id];
  }, [photonId, photonGroups]);

  const createDeployment = (d: RawForm) => {
    setLoading(true);
    const deployment = {
      name: d.name,
      photon_id: d.photon[d.photon.length - 1],
      resource_requirement: {
        memory: d.memory,
        cpu: d.cpu,
        min_replicas: d.min_replicas,
        accelerator_type: d.accelerator_type,
        accelerator_num: d.accelerator_num,
      },
    };
    void message.loading({
      content: "Creating deployment, please wait ...",
      key: "create-deployment-deployment",
      duration: 0,
    });
    deploymentService.create(deployment).subscribe({
      next: () => {
        message.destroy("create-deployment-deployment");
        void message.success("Create deployment success");
        refreshService.refresh();
        finish();
        setLoading(false);
      },
      error: () => {
        message.destroy("create-deployment-deployment");
        setLoading(false);
      },
    });
  };
  return photonGroups.length ? (
    <Form
      css={css`
        margin-top: 12px;
      `}
      requiredMark={false}
      labelCol={{ span: 8 }}
      wrapperCol={{ span: 16 }}
      style={{ maxWidth: 600 }}
      initialValues={{
        min_replicas: 1,
        cpu: 1,
        memory: 8192,
        photon: initPhoton,
      }}
      onFinish={(e) => createDeployment(e)}
      autoComplete="off"
    >
      <Form.Item
        label="Photon"
        name="photon"
        rules={[{ required: true, message: "Please select photon" }]}
      >
        <Cascader showSearch options={options} />
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
        <Input autoFocus placeholder="Deployment name" />
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
        <InputNumber style={{ width: "100%" }} min={1} />
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
        <InputNumber style={{ width: "100%" }} min={1} addonAfter="MB" />
      </Form.Item>
      <Form.Item label="Accelerator Type" name="accelerator_type">
        <Input style={{ width: "100%" }} placeholder="Accelerator Type" />
      </Form.Item>
      <Form.Item label="Accelerator Number" name="accelerator_num">
        <InputNumber
          style={{ width: "100%" }}
          placeholder="Accelerator Number"
        />
      </Form.Item>
      <Form.Item wrapperCol={{ offset: 8, span: 16 }}>
        <Button loading={loading} type="primary" htmlType="submit">
          Create
        </Button>
      </Form.Item>
    </Form>
  ) : (
    <Empty description="No photons yet, Please upload photon first" />
  );
};

export const CreateDeployment: FC<{ min?: boolean; photonId?: string }> = ({
  min = false,
  photonId,
}) => {
  const [open, setOpen] = useState(false);

  const openDrawer = () => {
    setOpen(true);
  };
  const closeDrawer = () => {
    setOpen(false);
  };

  return (
    <>
      {min ? (
        <Button
          size="small"
          type="text"
          icon={<DeploymentIcon />}
          onClick={openDrawer}
        >
          Deploy
        </Button>
      ) : (
        <Button
          type="primary"
          block
          icon={<PlusOutlined />}
          onClick={openDrawer}
        >
          Create Deployment
        </Button>
      )}
      <Drawer
        destroyOnClose
        size="large"
        contentWrapperStyle={{ maxWidth: "100%" }}
        title="Create Deployment"
        open={open}
        onClose={closeDrawer}
      >
        <CreateDeploymentDetail photonId={photonId} finish={closeDrawer} />
      </Drawer>
    </>
  );
};
