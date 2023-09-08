import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/workspace/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import {
  ChartLine,
  DataViewAlt,
  Terminal as CarbonTerminal,
} from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { css } from "@emotion/react";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const Container: FC<
  PropsWithChildren<{ deployment: Deployment; replicaId: string }>
> = ({ deployment, replicaId }) => {
  const { pathname } = useResolvedPath("");

  const items = [
    {
      key: `${pathname}/terminal`,
      label: (
        <>
          <CarbonIcon icon={<CarbonTerminal />} />
          Terminal
        </>
      ),
    },
    {
      key: `${pathname}/logs`,
      label: (
        <>
          <CarbonIcon icon={<DataViewAlt />} />
          Logs
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
  ];
  return (
    <Row gutter={[0, 24]}>
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
              title: (
                <LinkTo
                  name="deploymentDetail"
                  params={{ deploymentName: deployment.name }}
                  relative="route"
                >
                  <span>{deployment.name}</span>
                </LinkTo>
              ),
            },
            {
              title: (
                <LinkTo
                  name="deploymentDetailReplicasList"
                  params={{ deploymentName: deployment.name }}
                  relative="route"
                >
                  Replicas
                </LinkTo>
              ),
            },
            {
              title: replicaId,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card
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
