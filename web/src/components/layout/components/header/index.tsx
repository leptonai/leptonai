import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Input, Space } from "antd";
import { SearchOutlined, UserOutlined } from "@ant-design/icons";
import { LeptonIcon } from "@lepton-dashboard/components/icons/logo";

const Container = styled.div`
  height: 60px;
  padding: 0 24px;
  display: flex;
  flex: 0 0 60px;
`;

const LogoContainer = styled.div`
  flex: 0 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
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
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <LogoContainer>
        <LeptonIcon />
      </LogoContainer>
      <MenuContainer>
        <Space>
          <Input
            css={css`
              width: 300px;
            `}
            bordered={false}
            prefix={<SearchOutlined />}
            placeholder="Type / to search"
          />
          <Button
            shape="circle"
            type="text"
            icon={<UserOutlined />}
            target="_blank"
            href={`https://github.com/leptonai/lepton/commit/${__COMMIT_HASH__}`}
          />
        </Space>
      </MenuContainer>
    </Container>
  );
};
