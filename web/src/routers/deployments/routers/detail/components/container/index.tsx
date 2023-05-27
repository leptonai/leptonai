import { FC, PropsWithChildren } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/components/breadcrumb-header";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/components/link";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentItem } from "@lepton-dashboard/components/deployment-item";
import { css } from "@emotion/react";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import { BlockStorageAlt, Book, Play } from "@carbon/icons-react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Metrics } from "@lepton-dashboard/routers/deployments/routers/detail/components/metrics";

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
                  <Link to="/deployments/list" relative="route">
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
          <Outlet />
        </Card>
      </Col>
    </Row>
  );
};
