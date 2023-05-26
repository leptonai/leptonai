import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/components/link";
import { Card } from "@lepton-dashboard/components/card";
import { css } from "@emotion/react";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import {
  ChartLine,
  DataViewAlt,
  Terminal as CarbonTerminal,
} from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";

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
              title: instanceId,
            },
          ]}
        />
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
          <TabsNav menuItems={items} />
          <Card borderless shadowless>
            <Outlet />
          </Card>
        </Card>
      </Col>
    </Row>
  );
};
