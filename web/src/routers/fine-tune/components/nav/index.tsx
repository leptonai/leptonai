import { TabsProps } from "antd";
import { FC } from "react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Network_1, Table } from "@carbon/icons-react";
import { TabsNav } from "../../../../components/tabs-nav";
import { useResolvedPath } from "react-router-dom";

export const Nav: FC = () => {
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
  return <TabsNav menuItems={menuItems} />;
};
