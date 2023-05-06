import { FC, useMemo } from "react";
import {
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
import { useParams } from "react-router-dom";

export const Create: FC = () => {
  const modelService = useInject(ModelService);
  const groupedModels = useStateFromObservable(
    () => modelService.listGroup(),
    []
  );
  const { id } = useParams();
  const options = groupedModels.map((g) => {
    return {
      value: g.name,
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
    return [targetMode?.name, id || targetMode?.latest.id];
  }, [id, groupedModels]);
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
              labelCol={{ span: 8 }}
              wrapperCol={{ span: 16 }}
              style={{ maxWidth: 600 }}
              initialValues={{
                name: "Untitled deployment",
                min_replicas: 1,
                cpu: 1,
                memory: 8096,
                model: initModel,
              }}
              onFinish={(e) => console.log(e)}
              autoComplete="off"
            >
              <Form.Item
                label="Name"
                name="name"
                rules={[
                  { required: true, message: "Please input deployment name" },
                ]}
              >
                <Input autoFocus />
              </Form.Item>

              <Form.Item
                label="Model"
                name="model"
                rules={[{ required: true, message: "Please select model" }]}
              >
                <Cascader options={options} />
              </Form.Item>
              <Form.Item
                label="Min Replicas"
                name="min_replicas"
                rules={[{ required: true, message: "Please min replicas" }]}
              >
                <InputNumber />
              </Form.Item>
              <Form.Item
                label="CPU"
                name="cpu"
                rules={[{ required: true, message: "Please input cpu number" }]}
              >
                <InputNumber />
              </Form.Item>
              <Form.Item
                label="Memory"
                name="memory"
                rules={[{ required: true, message: "Please input memory" }]}
              >
                <InputNumber addonAfter="MB" />
              </Form.Item>
              <Form.Item label="Accelerator Type" name="accelerator_type">
                <Input placeholder="Accelerator Type" />
              </Form.Item>
              <Form.Item label="Accelerator Number" name="accelerator_num">
                <InputNumber placeholder="Number" />
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
