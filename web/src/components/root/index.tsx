import { FC, PropsWithChildren } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import styled from "@emotion/styled";

const Container = styled.div`
  height: 100%;
`;
export const Root: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${theme.colorBgLayout};
        font-family: ${theme.fontFamily};
        color: ${theme.colorText};
        font-size: ${theme.fontSize}px;
      `}
    >
      {children}
    </Container>
  );
};
