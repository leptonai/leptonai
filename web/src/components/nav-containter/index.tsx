import styled from "@emotion/styled";
import { FC, PropsWithChildren } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

const Container = styled.div`
  position: sticky;
  padding: 0 24px;
  z-index: 2;
  flex: 0 0 46px;
  top: 0;
`;

export const NavContainer: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();

  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: 1px solid ${theme.colorBorder};
        box-shadow: ${theme.boxShadowTertiary};
      `}
    >
      {children}
    </Container>
  );
};
