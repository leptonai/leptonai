import { FC, PropsWithChildren, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

const Container = styled.div`
  display: flex;
  flex-direction: column;
`;
const Header = styled.div`
  height: 60px;
  flex: 0 0 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;
const Title = styled.div`
  font-size: 18px;
  font-weight: 400;
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: start;
`;
const Extra = styled.div`
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: end;
`;
const Content = styled.div`
  flex: 1 1 auto;
  margin-top: 24px;
  margin-bottom: 24px;
`;
export const Section: FC<
  PropsWithChildren<{ title: ReactNode; extra?: ReactNode }>
> = ({ children, title, extra }) => {
  const theme = useAntdTheme();
  return (
    <Container>
      <Header>
        <Title
          css={css`
            color: ${theme.colorTextHeading};
            border-bottom: 1px solid ${theme.colorBorderSecondary};
          `}
        >
          {title}
        </Title>
        <Extra>{extra}</Extra>
      </Header>
      <Content>{children}</Content>
    </Container>
  );
};
