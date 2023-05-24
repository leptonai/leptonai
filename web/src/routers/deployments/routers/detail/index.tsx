import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Col, Row, Tabs } from "antd";
import { BreadcrumbHeader } from "../../../../components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Requests } from "../../components/requests";
import { css } from "@emotion/react";
import { BlockStorageAlt, Book, Play } from "@carbon/icons-react";
import { Apis } from "@lepton-dashboard/routers/deployments/components/apis";
import { Instances } from "@lepton-dashboard/routers/deployments/components/instances";
import { DeploymentItem } from "@lepton-dashboard/components/deployment-item";

export const Detail: FC = () => {
  const { id } = useParams();
  const deploymentService = useInject(DeploymentService);
  const deployment = useStateFromObservable(
    () => deploymentService.id(id!),
    undefined
  );

  return deployment ? (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <DeploymentIcon />
                  <Link to="../../deployments">
                    <span>Deployments</span>
                  </Link>
                </>
              ),
            },
            {
              title: deployment.name,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card>
          <DeploymentItem deployment={deployment} />
        </Card>
      </Col>
      <Col span={24}>
        <Card
          paddingless
          css={css`
            .ant-tabs-nav {
              margin-bottom: 0;
            }
            .ant-tabs-nav-wrap {
              margin: 0 16px;
            }
          `}
        >
          <Tabs
            tabBarGutter={32}
            items={[
              {
                key: "demo",
                label: (
                  <>
                    <CarbonIcon icon={<Play />} />
                    Demo
                  </>
                ),
                children: (
                  <Card shadowless borderless>
                    <Requests deployment={deployment} />
                  </Card>
                ),
              },
              {
                key: "api",
                label: (
                  <>
                    <CarbonIcon icon={<Book />} />
                    API
                  </>
                ),
                children: (
                  <Card shadowless borderless>
                    <Apis deployment={deployment} />
                  </Card>
                ),
              },
              {
                key: "instances",
                label: (
                  <>
                    <CarbonIcon icon={<BlockStorageAlt />} />
                    Instances
                  </>
                ),
                children: (
                  <Card shadowless borderless>
                    <Instances deployment={deployment} />
                  </Card>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  ) : null;
};
