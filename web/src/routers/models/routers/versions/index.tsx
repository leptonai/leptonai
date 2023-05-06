import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Col, Row, Timeline, Typography } from "antd";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { ModelCard } from "@lepton-dashboard/components/model-card";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import dayjs from "dayjs";

export const Versions: FC = () => {
  const { name } = useParams();
  const modelService = useInject(ModelService);
  const groupedModel = useStateFromObservable(
    () => modelService.getGroup(name!),
    undefined
  );
  const theme = useAntdTheme();
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
        <Card title="Version History">
          <Timeline
            css={css`
              padding: 8px 0;
            `}
            items={models.map((m) => {
              return {
                color: theme.colorTextSecondary,
                dot: <ExperimentOutlined />,
                children: (
                  <Col key={m.id} span={24}>
                    <Typography.Paragraph
                      style={{ paddingTop: "1px" }}
                      type="secondary"
                    >
                      Create at {dayjs(m.created_at).format("lll")}
                    </Typography.Paragraph>
                    <ModelCard shadowless={true} model={m} />
                  </Col>
                ),
              };
            })}
          />
        </Card>
      </Col>
    </Row>
  );
};
