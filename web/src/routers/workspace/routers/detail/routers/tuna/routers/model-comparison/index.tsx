import { ChatModelsComparison } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chat-models-comparison";
import { FC } from "react";
import { useParams } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/workspace/components/breadcrumb-header";
import { TunaIcon } from "@lepton-dashboard/components/icons";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { Card } from "@lepton-dashboard/components/card";

export const ModelComparison: FC = () => {
  const { name } = useParams();
  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <TunaIcon />
                  <LinkTo name="tunaList" relative="route">
                    <span>Tuna</span>
                  </LinkTo>
                </>
              ),
            },
            {
              title: "Chat",
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card paddingless>{name && <ChatModelsComparison name={name} />}</Card>
      </Col>
    </Row>
  );
};
