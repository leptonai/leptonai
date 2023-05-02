import { FC, ReactNode, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import styled from "@emotion/styled";

export const RouterLink: FC<{
  text: string;
  link: string;
  icon: ReactNode;
}> = ({ text, link, icon }) => {
  const theme = useAntdTheme();

  const Container = useMemo(
    () => styled(Link)`
      display: flex;
      align-items: center;
      text-decoration: none;
      transition: 0.25s ease;
      color: ${theme.colorTextSecondary};
      height: 48px;
      &:hover {
        color: ${theme.colorText};
        transform: translateX(4px);
      }
    `,
    [theme]
  );
  const TextContainer = useMemo(
    () => styled.span`
      font-size: 16px;
      font-weight: 400;
    `,
    []
  );
  const IconContainer = useMemo(
    () => styled.span`
      margin-right: 12px;
    `,
    []
  );
  return (
    <Container to={link}>
      <IconContainer>{icon}</IconContainer>
      <TextContainer>{text}</TextContainer>
    </Container>
  );
};
