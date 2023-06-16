import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/workspace/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { DeploymentItem } from "@lepton-dashboard/routers/workspace/components/deployment-item";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import { BlockStorageAlt, Book, Play } from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Metrics } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/metrics";
import { css } from "@emotion/react";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";

export const Container: FC<PropsWithChildren<{ deployment?: Deployment }>> = ({
  deployment,
}) => {
  const { pathname } = useResolvedPath("");
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

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
      key: `${pathname}/instances/list`,
      label: (
        <>
          <CarbonIcon icon={<BlockStorageAlt />} />
          Instances
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
              title: deployment?.name,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card>{deployment && <DeploymentItem deployment={deployment} />}</Card>
      </Col>
      <Col span={24}>
        <Card>{deployment && <Metrics deployment={deployment} />}</Card>
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
