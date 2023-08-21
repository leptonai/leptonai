import { css } from "@emotion/react";
import { Grid } from "antd";
import { FC } from "react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChatBot, Image } from "@carbon/icons-react";
import { TabsNav } from "../../../../components/tabs-nav";
import { useResolvedPath } from "react-router-dom";

const shareStyle = `
              .ant-tabs-tab-btn {
                position: relative;
                top: 1px;
                padding: 1px 5px;
              }
              .ant-tabs-tab {
                padding: 12px 0 !important;
              }
            `;

export const Nav: FC = () => {
  const { pathname } = useResolvedPath("");
  const { xs } = Grid.useBreakpoint();

  const menuItems = [
    {
      label: (
        <span id="nav-llama2">
          <CarbonIcon icon={<ChatBot />} />
          <span className="txt">Llama 2</span>
        </span>
      ),
      key: `${pathname}/llama2`,
    },
    {
      label: (
        <span id="nav-sdxl">
          <CarbonIcon icon={<Image />} />
          <span className="txt">Stable Diffusion XL</span>
        </span>
      ),
      key: `${pathname}/sdxl`,
    },
  ];

  return (
    <TabsNav
      css={
        xs
          ? css`
              .txt {
                display: none;
              }
              .anticon {
                margin-right: 0 !important;
              }
              .ant-tabs-tab + .ant-tabs-tab {
                margin-left: 8px !important;
              }
              ${shareStyle}
            `
          : css`
              ${shareStyle}
            `
      }
      menuItems={menuItems}
    />
  );
};
