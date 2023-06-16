import { NavContainer } from "@lepton-dashboard/components/nav-containter";
import { FC, PropsWithChildren, ReactNode } from "react";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

const Container = styled.div`
  height: 100%;
  overflow: auto;
`;

const Main = styled.div`
  min-height: 100%;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  padding: 24px;
`;

const FullHeight = styled.div`
  min-height: 100%;
  display: flex;
  flex-direction: column;
`;

export interface LayoutProps {
  header?: ReactNode;
  nav?: ReactNode;
  footer?: ReactNode;
}

export const Layout: FC<LayoutProps & PropsWithChildren> = ({
  children,
  nav,
  footer,
  header,
}) => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${theme.colorBgLayout};
      `}
    >
      <FullHeight>
        {header}
        {nav && <NavContainer>{nav}</NavContainer>}
        <Main
          css={css`
            background: ${theme.colorBgLayout};
          `}
        >
          {children}
        </Main>
      </FullHeight>
      {footer}
    </Container>
  );
};
