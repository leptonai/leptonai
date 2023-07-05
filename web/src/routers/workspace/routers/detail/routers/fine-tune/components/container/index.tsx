import { FC } from "react";
import { Outlet, useResolvedPath } from "react-router-dom";
import { Col, Row, TabsProps } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "../../../../../../../../components/card";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";
import { Network_1, Table } from "@carbon/icons-react";
import { css } from "@emotion/react";

export const Container: FC = () => {
  const { pathname } = useResolvedPath("");
  const menuItems: TabsProps["items"] = [
    {
      label: (
        <>
          <CarbonIcon icon={<Network_1 />} />
          New Fine Tune Job
        </>
      ),
      key: `${pathname}/create`,
    },
    {
      label: (
        <>
          <CarbonIcon icon={<Table />} />
          History Fine Tune Jobs
        </>
      ),
      key: `${pathname}/jobs`,
    },
  ];
  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <Card
          paddingless
          title={
            <TabsNav
              css={css`
                position: relative;
                bottom: -1px;
              `}
              menuItems={menuItems}
            />
          }
        >
          <div
            css={css`
              flex: 1 1 auto;
              position: relative;
              padding: 16px;
            `}
          >
            <Outlet />
          </div>
        </Card>
      </Col>
    </Row>
  );
};
