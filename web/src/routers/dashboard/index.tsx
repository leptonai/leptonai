import { FC } from "react";
import styled from "@emotion/styled";
import { Badge, Button, Card, Col, Row, Table, Typography } from "antd";
import {
  ExperimentOutlined,
  NumberOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { css } from "@emotion/react";

const Container = styled.div`
  flex: 1 1 auto;
`;
const models = [
  {
    id: "ce7387ad-bcdc-4a18-b7ca-2ad07adcf50b",
    key: "ce7387ad-bcdc-4a18-b7ca-2ad07adcf50b",
    name: "stabilityai/stablelm-tuned-alpha-chat_main",
    model_source: "hf:stabilityai/sd-1.5",
    requirement_dependency: ["pandas==0.23.1", "transformers==4.27.1"],
    image_url: "nvcr.io/nvidia/cuda:12.1.0-devel-ubuntu18.04",
    entrypoint: "cd /root/data && python main.py",
    exposed_ports: [8080, 5000],
    container_args: ["--shm=10g", "--cidfile=/path/to/file"],
    created_at: 0,
  },
  {
    id: "50d3c09a-063b-4c47-8272-46812ef29832",
    key: "50d3c09a-063b-4c47-8272-46812ef29832",
    name: "stabilityai/stablelm-tuned-alpha-chat_main",
    model_source: "hf:stabilityai/sd-1.5",
    requirement_dependency: ["pandas==0.23.1", "transformers==4.27.1"],
    image_url: "nvcr.io/nvidia/cuda:12.1.0-devel-ubuntu18.04",
    entrypoint: "cd /root/data && python main.py",
    exposed_ports: [8080, 5000],
    container_args: ["--shm=10g", "--cidfile=/path/to/file"],
    created_at: 0,
  },
];

const deployments = [
  {
    id: "35946b6e-7006-40fd-aa9b-6eba584d0b8",
    key: "35946b6e-7006-40fd-aa9b-6eba584d0b8",
    name: "dolly-v1.2",
    photon_id: "35946b6e-7006-40fd-aa9b-6eba584d0b8",
    status: {
      state: "success",
      endpoint: {
        internal_endpoint: "string",
        external_endpoint: "string",
      },
    },
    resource_requirement: {
      cpu: 4,
      memory: 4,
      accelerator_type: "Nvidia A100",
      accelerator_num: null,
      min_replica: 1,
    },
  },
];
export const Dashboard: FC = () => {
  return (
    <Container>
      <Row gutter={[16, 32]}>
        <Col span={6}>
          <Card
            css={css`
              height: 200px;
            `}
            title="Total Models"
            bordered={false}
          >
            <Typography.Title>10</Typography.Title>
          </Card>
        </Col>
        <Col span={18}>
          <Card
            css={css`
              height: 200px;
            `}
            bordered={false}
            title="Recent Models"
          >
            <Table
              size="small"
              pagination={false}
              bordered={false}
              showHeader={false}
              columns={[
                {
                  dataIndex: "id",
                  render: (value) => (
                    <Button type="text" icon={<NumberOutlined />}>
                      {value}
                    </Button>
                  ),
                },
                {
                  dataIndex: "name",
                  render: (value) => (
                    <Button type="link" icon={<ExperimentOutlined />}>
                      {value}
                    </Button>
                  ),
                },
                {
                  dataIndex: "exposed_ports",
                  render: (value) => value.join(","),
                },
              ]}
              dataSource={models}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            css={css`
              height: 200px;
            `}
            title="Total Deployments"
            bordered={false}
          >
            <Typography.Title>32</Typography.Title>
          </Card>
        </Col>
        <Col span={18}>
          <Card
            css={css`
              height: 200px;
            `}
            bordered={false}
            title="Recent Deployments"
          >
            <Table
              size="small"
              pagination={false}
              bordered={false}
              showHeader={false}
              columns={[
                {
                  dataIndex: "id",
                  render: (value) => (
                    <Button type="text" icon={<NumberOutlined />}>
                      {value}
                    </Button>
                  ),
                },
                {
                  dataIndex: "name",
                  render: (value) => (
                    <Button type="link" icon={<RocketOutlined />}>
                      {value}
                    </Button>
                  ),
                },
                {
                  dataIndex: "status",
                  render: () => <Badge status="success" text="Running" />,
                },
              ]}
              dataSource={deployments}
            />
          </Card>
        </Col>
      </Row>
    </Container>
  );
};
