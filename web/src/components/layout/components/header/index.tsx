import { FC, useMemo } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Input, Space } from "antd";
import { SearchOutlined, UserOutlined } from "@ant-design/icons";
import { LeptonIcon } from "@lepton-dashboard/components/icons/logo";
import { useInject } from "@lepton-libs/di";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";

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
  const titleService = useInject(TitleService);
  const title = useStateFromObservable(() => titleService.title$, undefined);
  const Text = useMemo(
    () => styled.div`
      font-size: 22px;
      margin-left: 16px;
      color: ${theme.colorTextTertiary};
      font-weight: 300;
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
            font-weight: 200;
          `}
        >
          /
        </Text>
        <Text
          css={css`
            color: ${theme.colorTextHeading};
          `}
        >
          {title}
        </Text>
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
