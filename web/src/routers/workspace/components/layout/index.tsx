import { FC, PropsWithChildren } from "react";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Nav } from "@lepton-dashboard/routers/workspace/components/layout/components/nav";
import { Footer } from "@lepton-dashboard/routers/workspace/components/layout/components/footer";
import { Header } from "@lepton-dashboard/routers/workspace/components/layout/components/header";

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

export const Layout: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${theme.colorBgLayout};
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
          {children}
        </Main>
      </FullHeight>

      <Footer />
    </Container>
  );
};
