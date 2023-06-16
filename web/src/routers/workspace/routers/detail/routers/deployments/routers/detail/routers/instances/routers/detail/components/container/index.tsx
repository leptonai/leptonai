import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/workspace/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import {
  ChartLine,
  DataViewAlt,
  Terminal as CarbonTerminal,
} from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { css } from "@emotion/react";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";

export const Container: FC<
  PropsWithChildren<{ deployment: Deployment; instanceId: string }>
> = ({ deployment, instanceId }) => {
  const { pathname } = useResolvedPath("");
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

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
                  <Link
                    to={`/workspace/${workspaceTrackerService.name}/deployments/list`}
                    relative="route"
                  >
                    <span>Deployments</span>
                  </Link>
                </>
              ),
            },
            {
              title: (
                <Link
                  to={`/workspace/${workspaceTrackerService.name}/deployments/detail/${deployment.id}`}
                  relative="route"
                >
                  <span>{deployment.name}</span>
                </Link>
              ),
            },
            {
              title: (
                <Link
                  to={`/workspace/${workspaceTrackerService.name}/deployments/detail/${deployment.id}/instances/list`}
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
