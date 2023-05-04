import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Card, Descriptions } from "antd";
import { DetailDescription } from "@lepton-dashboard/routers/models/components/detail-description";
import dayjs from "dayjs";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";

export const Detail: FC = () => {
  const { id } = useParams();
  const modelService = useInject(ModelService);
  const model = useStateFromObservable(
    () => modelService.getModel(id!),
    undefined
  );

  return model ? (
    <>
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
              title: (
                <Link to={`../../versions/${model.name}`}>{model.name}</Link>
              ),
            },
            {
              title: model.id,
            },
          ]}
        />
      </BreadcrumbHeader>
      <Card title="Detail">
        <DetailDescription model={model}>
          <Descriptions.Item label="Name">{model.name}</Descriptions.Item>
          <Descriptions.Item label="Id">{model.id}</Descriptions.Item>
          <Descriptions.Item label="Created Time">
            {dayjs(model.created_at).format("lll")}
          </Descriptions.Item>

          <Descriptions.Item label="Source">
            {model.model_source}
          </Descriptions.Item>
        </DetailDescription>
      </Card>
    </>
  ) : null;
};
