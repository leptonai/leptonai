import { FC, useMemo } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Input, Space } from "antd";

import { LeptonIcon } from "@lepton-dashboard/components/icons";
import {
  GithubOutlined,
  ReadOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const Container = styled.div`
  height: 50px;
  padding: 0 24px;
  display: flex;
  flex: 0 0 50px;
  flex-wrap: wrap;
  overflow: hidden;
  z-index: 2;
`;

const LogoContainer = styled.div`
  flex: 0 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  margin-right: 24px;
`;

const MenuContainer = styled.div`
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: end;
`;

export const Header: FC = () => {
  const theme = useAntdTheme();
  const Text = useMemo(
    () => styled.div`
      font-size: 20px;
      margin-left: 16px;
      color: ${theme.colorTextTertiary};
      cursor: default;
      font-weight: 600;
    `,
    [theme]
  );
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <LogoContainer>
        <LeptonIcon />
        <Text
          css={css`
            color: ${theme.colorTextHeading};
          `}
        >
          Lepton AI
        </Text>
      </LogoContainer>
      <MenuContainer>
        <Space>
          <Input
            css={css`
              width: 300px;
            `}
            prefix={<SearchOutlined />}
            placeholder="Type / to search"
          />
          <Button
            href="https://www.lepton.ai"
            target="_blank"
            type="text"
            icon={<ReadOutlined />}
          />
          <Button
            type="text"
            href="https://github.com/leptonai/lepton"
            target="_blank"
            icon={<GithubOutlined />}
          />
        </Space>
      </MenuContainer>
    </Container>
  );
};
