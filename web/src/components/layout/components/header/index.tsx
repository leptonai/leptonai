import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { FC, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Space } from "antd";
import { Logo } from "@lepton-dashboard/components/logo";

const Container = styled.div`
  height: 50px;
  padding: 0 32px;
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

export const Header: FC<HeaderProps & EmotionProps> = ({
  menu,
  actions,
  className,
}) => {
  const theme = useAntdTheme();

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
        `}
      >
        <Logo />
        {menu}
      </div>

      <MenuContainer>
        <Space>{actions}</Space>
      </MenuContainer>
    </Container>
  );
};
