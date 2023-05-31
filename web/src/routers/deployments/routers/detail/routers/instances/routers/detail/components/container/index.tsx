import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/components/link";
import { Card } from "@lepton-dashboard/components/card";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import {
  ChartLine,
  DataViewAlt,
  Terminal as CarbonTerminal,
} from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { css } from "@emotion/react";

export const Container: FC<
  PropsWithChildren<{ deployment: Deployment; instanceId: string }>
> = ({ deployment, instanceId }) => {
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
                  <Link to="/deployments/list" relative="route">
                    <span>Deployments</span>
                  </Link>
                </>
              ),
            },
            {
              title: (
                <Link
                  to={`/deployments/detail/${deployment.id}`}
                  relative="route"
                >
                  <span>{deployment.name}</span>
                </Link>
              ),
            },
            {
              title: (
                <Link
                  to={`/deployments/detail/${deployment.id}/instances/list`}
                  relative="route"
                >
                  Instances
                </Link>
              ),
            },
            {
              title: instanceId,
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
