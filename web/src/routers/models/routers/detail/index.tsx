import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";
import { ModelCard } from "@lepton-dashboard/components/model-card";

export const Detail: FC = () => {
  const { id } = useParams();
  const modelService = useInject(ModelService);
  const model = useStateFromObservable(
    () => modelService.getById(id!),
    undefined
  );

  return model ? (
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
      </Col>
      <Col span={24}>
        <ModelCard model={model} detail={true} />
      </Col>
    </Row>
  ) : null;
};
