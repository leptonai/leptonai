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
  height: 48px;
  display: flex;
  flex: 0 0 48px;
  flex-wrap: nowrap;
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
  border?: boolean;
  content?: ReactNode;
  hideDefaultActions?: boolean;
  enableLogoHref?: boolean;
}

export const Header: FC<HeaderProps & EmotionProps> = ({
  menu,
  actions,
  className,
  border = false,
  content,
  hideDefaultActions = false,
  enableLogoHref = false,
}) => {
  const theme = useAntdTheme();
  const { xs } = Grid.useBreakpoint();

  return (
    <Container
      className={className}
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: ${border ? "1px" : 0} solid ${theme.colorBorder};
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
        <Logo enableLogoHref={enableLogoHref} />
        {menu}
      </div>
      {content}
      <MenuContainer>
        <Space>
          {!hideDefaultActions && (
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
          )}
          {actions}
        </Space>
      </MenuContainer>
    </Container>
  );
};
