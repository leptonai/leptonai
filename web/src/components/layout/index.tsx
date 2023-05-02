import { FC } from "react";
import { Outlet } from "react-router-dom";
import styled from "@emotion/styled";
import { Nav } from "@lepton-dashboard/components/layout/components/nav";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Logo } from "@lepton-dashboard/components/layout/components/logo";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";

const Container = styled.div`
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: 180px minmax(max-content, 1fr);
  column-gap: 60px;
  padding: 24px 100px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03),
    0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
`;

const Root = styled.div`
  height: 100%;
  padding: 32px;
  display: flex;
`;

const SideBar = styled.div`
  display: flex;
  flex-direction: column;
`;
const Main = styled.div``;

export const Layout: FC = () => {
  const theme = useAntdTheme();
  return (
    <Root
      css={css`
        background: ${theme.colorBgLayout};
        font-family: ${theme.fontFamily};
      `}
    >
      <Container
        css={css`
          background: ${theme.colorBgContainer};
        `}
      >
        <SideBar>
          <Logo />
          <Nav />
          <Footer />
        </SideBar>
        <Main>
          <Outlet />
        </Main>
      </Container>
    </Root>
  );
};
