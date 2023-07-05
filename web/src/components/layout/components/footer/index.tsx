import { Asleep, Light } from "@carbon/icons-react";
import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button } from "antd";
import { CarbonIcon, LeptonFillIcon } from "@lepton-dashboard/components/icons";
import { GithubOutlined, TwitterOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
const Container = styled.div`
  height: 56px;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 32px;
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
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: end;
`;

export const Footer: FC = () => {
  const theme = useAntdTheme();
  const themeService = useInject(ThemeService);

  return (
    <Container
      css={css`
        border-top: 1px solid ${theme.colorBorder};
        font-weight: normal;
        display: flex;
        justify-content: space-between;
        background: ${theme.colorBgContainer};
      `}
    >
      <Logo>
        <LeptonFillIcon />
        <Text>Lepton AI</Text>
      </Logo>
      <Button
        type="text"
        onClick={() => themeService.toggleTheme()}
        icon={
          themeService.getValidTheme() === "dark" ? (
            <CarbonIcon icon={<Asleep />} />
          ) : (
            <CarbonIcon icon={<Light />} />
          )
        }
      />
      <MenuContainer>
        <Button
          type="text"
          rel="noreferrer"
          href="https://twitter.com/leptonai"
          target="_blank"
          icon={<TwitterOutlined />}
        />
        <Button
          type="text"
          rel="noreferrer"
          href="https://github.com/leptonai"
          target="_blank"
          icon={<GithubOutlined />}
        />
      </MenuContainer>
    </Container>
  );
};
