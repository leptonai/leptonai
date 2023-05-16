import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Switch } from "antd";
import { CarbonIcon, LeptonFillIcon } from "@lepton-dashboard/components/icons";
import {
  GithubOutlined,
  ReadOutlined,
  TwitterOutlined,
} from "@ant-design/icons";
import { AsleepFilled, LightFilled } from "@carbon/icons-react";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";
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
const ThemeContainer = styled.div`
  display: flex;
  align-items: center;
  margin-left: 24px;
  justify-content: center;
`;

export const Footer: FC = () => {
  const theme = useAntdTheme();
  const themeService = useInject(ThemeService);

  return (
    <Container
      css={css`
        border-top: 1px solid ${theme.colorBorder};
        font-weight: normal;
        background: ${theme.colorBgContainer};
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
        <ThemeContainer>
          <Switch
            size="small"
            css={css`
              background: ${theme.colorTextTertiary} !important;
              .ant-switch-inner-checked,
              .ant-switch-inner-unchecked {
                color: ${theme.colorBgContainer} !important;
              }
            `}
            checked={themeService.getValidTheme() === "dark"}
            onChange={() => themeService.toggleTheme()}
            unCheckedChildren={<CarbonIcon icon={<LightFilled />} />}
            checkedChildren={<CarbonIcon icon={<AsleepFilled />} />}
          />
        </ThemeContainer>
      </MenuContainer>
    </Container>
  );
};
