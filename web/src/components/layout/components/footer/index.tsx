import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button } from "antd";
import { LeptonFillIcon } from "@lepton-dashboard/components/icons/logo";
import {
  GithubOutlined,
  ReadOutlined,
  TwitterOutlined,
} from "@ant-design/icons";
const Container = styled.div`
  height: 60px;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 24px;
  justify-content: space-between;
  flex-wrap: wrap;
`;

const Logo = styled.div`
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  margin-right: 24px;
`;
const Text = styled.div`
  margin-left: 8px;
  cursor: default;
`;
const MenuContainer = styled.div`
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: end;
`;
export const Footer: FC = () => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        border-top: 1px solid ${theme.colorBorder};
        font-weight: normal;
      `}
    >
      <Logo>
        <LeptonFillIcon />
        <Text>Lepton AI</Text>
      </Logo>
      <MenuContainer>
        <Button
          href="https://www.lepton.ai"
          target="_blank"
          type="text"
          icon={<ReadOutlined />}
        >
          Documents
        </Button>
        <Button
          type="text"
          href="https://github.com/leptonai/lepton"
          target="_blank"
          icon={<GithubOutlined />}
        >
          Github
        </Button>
        <Button
          type="text"
          href="https://twitter.com/leptonai"
          target="_blank"
          icon={<TwitterOutlined />}
        >
          Twitter
        </Button>
      </MenuContainer>
    </Container>
  );
};
