import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Col, Row, Table } from "antd";
import { ColumnType } from "rc-table/lib/interface";
import { Model } from "@lepton-dashboard/interfaces/model.ts";
import dayjs from "dayjs";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { DetailDescription } from "@lepton-dashboard/routers/models/components/detail-description";
import { Card } from "@lepton-dashboard/components/card";

const optionalRender: ColumnType<Model>["render"] = (v) =>
  (Array.isArray(v) ? v.join(", ") : v) || "-";
const timeRender: ColumnType<Model>["render"] = (v) => dayjs(v).format("lll");

export const Versions: FC = () => {
  const { name } = useParams();
  const modelService = useInject(ModelService);
  const groupedModel = useStateFromObservable(
    () => modelService.getGroup(name!),
    undefined
  );
  const models = groupedModel?.data || [];
  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
            items={[
              {
                title: (
                  <>
                    <ExperimentOutlined />
                    <Link to="../../models">
                      <span>Models</span>
                    </Link>
                  </>
                ),
              },
              {
                title: name,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Latest Version">
          {groupedModel?.latest && (
            <DetailDescription model={groupedModel?.latest} />
          )}
        </Card>
      </Col>
      <Col span={24}>
        <Card title="History Versions">
          <Table
            bordered
            pagination={false}
            tableLayout="fixed"
            rowKey="id"
            size="small"
            columns={[
              {
                ellipsis: true,
                dataIndex: "id",
                title: "Id",
                render: (value) => (
                  <Link to={`../../detail/${value}`}>{value}</Link>
                ),
              },
              { ellipsis: true, dataIndex: "name", title: "Name" },
              {
                ellipsis: true,
                dataIndex: "model_source",
                title: "Model Source",
              },
              {
                ellipsis: true,
                dataIndex: "image_url",
                title: "Image URL",
              },
              {
                ellipsis: true,
                dataIndex: "created_at",
                title: "Created Time",
                render: timeRender,
              },
              {
                ellipsis: true,
                dataIndex: "exposed_ports",
                title: "Exposed Ports",
                render: optionalRender,
              },
              {
                ellipsis: true,
                dataIndex: "requirement_dependency",
                title: "Requirement Dependency",
                render: optionalRender,
              },
              {
                ellipsis: true,
                dataIndex: "container_args",
                title: "Container Args",
                render: optionalRender,
              },
              {
                ellipsis: true,
                dataIndex: "entrypoint",
                title: "Entrypoint",
                render: optionalRender,
              },
              {
                ellipsis: true,
                dataIndex: "id",
                title: "Action",
                render: (value) => (
                  <Link to={`../../detail/${value}`}>Detail</Link>
                ),
              },
            ]}
            dataSource={models}
          />
        </Card>
      </Col>
    </Row>
  );
};
