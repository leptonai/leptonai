import { FC, useMemo } from "react";
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
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { RocketOutlined } from "@ant-design/icons";
import { Link } from "@lepton-dashboard/components/link";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
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
  model: string[];
}

export const Create: FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const modelService = useInject(ModelService);
  const deploymentService = useInject(DeploymentService);
  const groupedModels = useStateFromObservable(() => modelService.groups(), []);
  const { id } = useParams();
  const options = groupedModels.map((g) => {
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
  const initModel = useMemo(() => {
    const targetMode =
      groupedModels.find((g) => g.latest.id === id) || groupedModels[0];
    return [targetMode?.latest.id, id || targetMode?.latest.id];
  }, [id, groupedModels]);

  const createDeployment = (d: RawForm) => {
    const deployment = {
      name: d.name,
      photon_id: d.model[d.model.length - 1],
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
      },
      error: () => {
        message.destroy("create-deployment");
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
          {groupedModels.length ? (
            <Form
              css={css`
                margin-top: 12px;
              `}
              requiredMark={false}
              labelCol={{ span: 8 }}
              wrapperCol={{ span: 16 }}
              style={{ maxWidth: 600 }}
              initialValues={{
                name: "deployment",
                min_replicas: 1,
                cpu: 1,
                memory: 8192,
                model: initModel,
              }}
              onFinish={(e) => createDeployment(e)}
              autoComplete="off"
            >
              <Form.Item
                label="Model"
                name="model"
                rules={[{ required: true, message: "Please select model" }]}
              >
                <Cascader options={options} />
              </Form.Item>
              <Form.Item
                label="Deployment Name"
                name="name"
                rules={[
                  { required: true, message: "Please input deployment name" },
                ]}
              >
                <Input autoFocus />
              </Form.Item>
              <Form.Item label="Min Replicas" name="min_replicas">
                <InputNumber style={{ width: "100%" }} min={0} />
              </Form.Item>
              <Form.Item label="CPU" name="cpu">
                <InputNumber style={{ width: "100%" }} min={1} />
              </Form.Item>
              <Form.Item label="Memory" name="memory">
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
                <Button type="primary" htmlType="submit">
                  Create
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Empty description="No models yet, Please upload model first" />
          )}
        </Card>
      </Col>
    </Row>
  );
};
