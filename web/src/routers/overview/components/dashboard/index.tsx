import { FC } from "react";
import { Section } from "@lepton-dashboard/components/section";
import { Badge, Table } from "antd";

const dataSource = [
  {
    id: 10,
    key: 1,
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
    id: 10,
    key: 2,
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
    id: 10,
    key: 3,
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
    id: 10,
    key: 4,
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

const columns = [
  {
    title: "Status",
    dataIndex: "key",
    render: () => <Badge status="success" text="Running" />,
  },
  {
    title: "Name",
    dataIndex: "name",
    key: "name",
  },
  {
    title: "Source",
    dataIndex: "model_source",
    key: "model_source",
  },
  {
    title: "Image URL",
    dataIndex: "image_url",
    key: "image_url",
  },
];

export const Dashboard: FC = () => {
  return (
    <Section title="Deployments">
      <Table
        size="middle"
        pagination={false}
        dataSource={dataSource}
        columns={columns}
      />
    </Section>
  );
};
