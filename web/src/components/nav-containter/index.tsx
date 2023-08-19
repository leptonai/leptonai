import styled from "@emotion/styled";
import { FC, PropsWithChildren } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

const Container = styled.div`
  position: sticky;
  z-index: 2;
  flex: 0 0 46px;
  top: 0;
  padding: 0 16px;
  @media (min-width: 600px) {
    padding: 0 32px;
  }
`;

export const NavContainer: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();

  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: 1px solid ${theme.colorBorder};
      `}
    >
      {children}
    </Container>
  );
};
