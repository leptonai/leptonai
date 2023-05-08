import { FC, useMemo, useState } from "react";
import {
  App,
  Breadcrumb,
  Button,
  Cascader,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
} from "antd";
import { Card } from "@lepton-dashboard/components/card";
import { css } from "@emotion/react";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/photons/components/breadcrumb-header";
import { RocketOutlined } from "@ant-design/icons";
import { Link } from "@lepton-dashboard/components/link";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import dayjs from "dayjs";
import { useNavigate, useParams } from "react-router-dom";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";

interface RawForm {
  name: string;
  min_replicas: number;
  accelerator_num?: number;
  accelerator_type?: string;
  cpu: number;
  memory: number;
  photon: string[];
}

export const Create: FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const photonService = useInject(PhotonService);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const groupedPhotons = useStateFromObservable(
    () => photonService.groups(),
    []
  );
  const { id } = useParams();
  const options = groupedPhotons.map((g) => {
    return {
      value: g.latest.id,
      label: g.name,
      children: g.data.map((i) => {
        return {
          value: i.id,
          label: dayjs(i.created_at).format("lll"),
        };
      }),
    };
  });
  const initPhoton = useMemo(() => {
    const targetMode =
      groupedPhotons.find((g) => g.latest.id === id) || groupedPhotons[0];
    return [targetMode?.latest.id, id || targetMode?.latest.id];
  }, [id, groupedPhotons]);

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
      key: "create-deployment",
      duration: 0,
    });
    deploymentService.create(deployment).subscribe({
      next: () => {
        message.destroy("create-deployment");
        void message.success("Create deployment success");
        navigate("/deployments");
        setLoading(false);
      },
      error: () => {
        message.destroy("create-deployment");
        setLoading(false);
      },
    });
  };
  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
            items={[
              {
                title: (
                  <>
                    <RocketOutlined />
                    <Link to="../../deployments">
                      <span>Deployments</span>
                    </Link>
                  </>
                ),
              },
              {
                title: "Create Deployment",
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Create Deployment">
          {groupedPhotons.length ? (
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
                <Cascader options={options} />
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
                <InputNumber
                  style={{ width: "100%" }}
                  min={1}
                  addonAfter="MB"
                />
              </Form.Item>
              <Form.Item label="Accelerator Type" name="accelerator_type">
                <Input
                  style={{ width: "100%" }}
                  placeholder="Accelerator Type"
                />
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
          )}
        </Card>
      </Col>
    </Row>
  );
};
