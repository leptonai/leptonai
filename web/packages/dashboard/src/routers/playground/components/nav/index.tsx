import { css } from "@emotion/react";
import { Grid } from "antd";
import { FC } from "react";
import { TabsNav } from "../../../../components/tabs-nav";
import { useResolvedPath } from "react-router-dom";

export const Nav: FC = () => {
  const { pathname } = useResolvedPath("");
  const { xs } = Grid.useBreakpoint();

  const menuItems = [
    {
      label: <span id="nav-llama2">Llama 2</span>,
      key: `${pathname}/llama2`,
    },
    {
      label: <span id="nav-sdxl">Stable Diffusion XL</span>,
      key: `${pathname}/sdxl`,
    },
  ];

  return !xs ? (
    <TabsNav
      css={css`
        margin-left: 36px;
        margin-top: 2px;
      `}
      menuItems={menuItems}
    />
  ) : null;
};
