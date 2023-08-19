import { Book } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { FC, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Grid, Space } from "antd";
import { Logo } from "@lepton-dashboard/components/logo";

const Container = styled.div`
  height: 50px;
  display: flex;
  flex: 0 0 50px;
  flex-wrap: nowrap;
  overflow: hidden;
  z-index: 2;
  padding: 0 16px;
  @media (min-width: 600px) {
    padding: 0 32px;
  }
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

export const Header: FC<HeaderProps & EmotionProps> = ({
  menu,
  actions,
  className,
}) => {
  const theme = useAntdTheme();
  const { xs } = Grid.useBreakpoint();

  return (
    <Container
      className={className}
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <div
        css={css`
          height: 100%;
          display: flex;
          flex: 0 1 auto;
          overflow: hidden;
        `}
      >
        <Logo />
        {menu}
      </div>

      <MenuContainer>
        <Space>
          <Button
            rel="noreferrer"
            href="https://www.lepton.ai/docs"
            target="_blank"
            type="text"
            size="small"
            icon={<CarbonIcon icon={<Book />} />}
          >
            {xs ? null : <span>Docs</span>}
          </Button>
          {actions}
        </Space>
      </MenuContainer>
    </Container>
  );
};
