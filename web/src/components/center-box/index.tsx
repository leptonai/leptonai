import {
  GithubOutlined,
  ReadOutlined,
  TwitterOutlined,
} from "@ant-design/icons";
import { Logo } from "@lepton-dashboard/components/logo";
import { Button, Divider, Space } from "antd";
import { FC, PropsWithChildren } from "react";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
export const CenterBox: FC<PropsWithChildren<{ width?: string }>> = ({
  children,
  width = `360px`,
}) => {
  const theme = useAntdTheme();

  return (
    <div
      css={css`
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
      `}
    >
      <div
        css={css`
          flex: 0 0 auto;
          width: ${width};
        `}
      >
        <Logo size="large" />
      </div>
      <div
        css={css`
          flex: 0 1 auto;
          width: ${width};
          padding: 32px;
          margin: 24px 0;
          * {
            transition: none !important;
          }
          display: flex;
          flex-direction: column;
          text-align: center;
          border-style: solid;
          border-color: ${theme.colorTextHeading};
          border-width: 1px 0;
          background: ${theme.colorBgContainer};
        `}
      >
        {children}
      </div>
      <div
        css={css`
          width: ${width};
          text-align: center;
        `}
      >
        <Space split={<Divider type="vertical" />}>
          <Button
            rel="noreferrer"
            href="https://www.lepton.ai"
            target="_blank"
            type="text"
            icon={<ReadOutlined />}
          />
          <Button
            type="text"
            rel="noreferrer"
            href="https://github.com/leptonai"
            target="_blank"
            icon={<GithubOutlined />}
          />
          <Button
            type="text"
            rel="noreferrer"
            href="https://twitter.com/leptonai"
            target="_blank"
            icon={<TwitterOutlined />}
          />
        </Space>
      </div>
    </div>
  );
};
