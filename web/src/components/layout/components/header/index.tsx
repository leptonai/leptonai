import { FC, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Space } from "antd";
import { GithubOutlined, ReadOutlined } from "@ant-design/icons";
import { Logo } from "@lepton-dashboard/components/logo";

const Container = styled.div`
  height: 50px;
  padding: 0 24px;
  display: flex;
  flex: 0 0 50px;
  flex-wrap: wrap;
  overflow: hidden;
  z-index: 2;
`;

const MenuContainer = styled.div`
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: end;
`;

export interface HeaderProps {
  menu?: ReactNode;
  actions?: ReactNode;
}

export const Header: FC<HeaderProps> = ({ menu, actions }) => {
  const theme = useAntdTheme();

  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <div
        css={css`
          height: 100%;
          display: flex;
        `}
      >
        <Logo />
        {menu}
      </div>

      <MenuContainer>
        <Space>
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
          {actions}
        </Space>
      </MenuContainer>
    </Container>
  );
};
