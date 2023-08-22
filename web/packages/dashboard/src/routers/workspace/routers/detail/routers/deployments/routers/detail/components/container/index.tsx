import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/workspace/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentItem } from "@lepton-dashboard/routers/workspace/components/deployment-item";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import {
  Book,
  ChartLine,
  EventSchedule,
  Play,
  Replicate,
} from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { css } from "@emotion/react";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const Container: FC<PropsWithChildren<{ deployment?: Deployment }>> = ({
  deployment,
}) => {
  const { pathname } = useResolvedPath("");

  const items = [
    {
      key: `${pathname}/demo`,
      label: (
        <>
          <CarbonIcon icon={<Play />} />
          Demo
        </>
      ),
    },
    {
      key: `${pathname}/api`,
      label: (
        <>
          <CarbonIcon icon={<Book />} />
          API
        </>
      ),
    },
    {
      key: `${pathname}/metrics`,
      label: (
        <>
          <CarbonIcon icon={<ChartLine />} />
          Metrics
        </>
      ),
    },
    {
      key: `${pathname}/events`,
      label: (
        <>
          <CarbonIcon icon={<EventSchedule />} />
          Events
        </>
      ),
    },
    {
      key: `${pathname}/replicas/list`,
      label: (
        <>
          <CarbonIcon icon={<Replicate />} />
          Replicas
        </>
      ),
    },
  ];
  return (
    <Row gutter={[0, 16]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <DeploymentIcon />
                  <LinkTo name="deploymentsList" relative="route">
                    <span>Deployments</span>
                  </LinkTo>
                </>
              ),
            },
            {
              title: deployment?.name,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card>{deployment && <DeploymentItem deployment={deployment} />}</Card>
      </Col>
      <Col span={24}>
        <Card
          paddingless
          title={
            <TabsNav
              css={css`
                position: relative;
                bottom: -1px;
              `}
              menuItems={items}
            />
          }
        >
          <Outlet />
        </Card>
      </Col>
    </Row>
  );
};
