import { FC, ReactNode } from "react";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export const CardContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: 24px;
  row-gap: 24px;
`;

export const Container = styled.div`
  flex: 1 1 auto;
  padding: 16px 32px;
  min-height: 100px;
  display: flex;
  justify-content: space-between;
  position: relative;
  cursor: default;
`;

const Icon = styled.div`
  flex: 0 0 40px;
  font-size: 36px;
  display: flex;
  align-items: center;
`;
const Content = styled.div`
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  margin-left: 24px;
`;
const Title = styled.div`
  font-weight: 500;
  font-size: 16px;
`;
const Data = styled.div`
  font-weight: 400;
  font-size: 16px;
  margin-top: 4px;
`;
export const Card: FC<{
  icon: ReactNode;
  title: ReactNode;
  data: ReactNode;
  color: string;
}> = ({ icon, title, data, color }) => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${color};
        color: ${theme.colorText};
      `}
    >
      <Icon>{icon}</Icon>
      <Content>
        <Title>{title}</Title>
        <Data>{data}</Data>
      </Content>
    </Container>
  );
};
