import { FC } from "react";
import { Outlet } from "react-router-dom";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Header } from "@lepton-dashboard/components/layout/components/header";
import { Nav } from "@lepton-dashboard/components/layout/components/nav";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";

const Container = styled.div`
  height: 100%;
  overflow: auto;
`;

const Main = styled.div`
  min-height: 100%;
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

export const Layout: FC = () => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <FullHeight>
        <Header />
        <Nav />
        <Main
          css={css`
            background: ${theme.colorBgLayout};
          `}
        >
          <Outlet />
        </Main>
      </FullHeight>

      <Footer />
    </Container>
  );
};
