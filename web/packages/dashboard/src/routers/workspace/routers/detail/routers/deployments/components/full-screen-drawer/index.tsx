import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";
import { Button, Drawer } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const FullScreenDrawer: FC<
  PropsWithChildren<{
    borderless?: boolean;
    open: boolean;
    onClose: () => void;
  }>
> = ({ children, open, onClose, borderless = false }) => {
  const theme = useAntdTheme();
  return (
    <Drawer
      css={css`
        .ant-drawer-header {
          display: none;
        }
      `}
      height="100%"
      bodyStyle={{ padding: 0 }}
      placement="bottom"
      onClose={onClose}
      destroyOnClose
      open={open}
    >
      <div
        css={css`
          height: 100%;
          display: flex;
          padding: 36px 18px 18px 18px;
          flex-direction: column;
          background: ${theme.colorBgLayout};
        `}
      >
        <Button
          type="text"
          size="small"
          onClick={onClose}
          css={css`
            position: absolute;
            top: 6px;
            right: 16px;
            z-index: 2;
          `}
          icon={<CloseOutlined />}
        />
        <div
          css={css`
            height: 100%;
            border: 1px solid ${borderless ? "transparent" : theme.colorBorder};
            border-radius: ${theme.borderRadius}px;
            overflow: hidden;
          `}
        >
          {children}
        </div>
      </div>
    </Drawer>
  );
};
