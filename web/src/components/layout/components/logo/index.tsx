import { FC } from "react";
import styled from "@emotion/styled";
import { LeptonIcon } from "@lepton-dashboard/components/icons/logo";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
const Container = styled.div`
  display: flex;
  height: 60px;
  font-size: 160px;
  flex: 0 0 60px;
`;
export const Logo: FC = () => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        color: ${theme.colorTextHeading};
        border-bottom: 1px solid ${theme.colorBorderSecondary};
      `}
    >
      <LeptonIcon />
    </Container>
  );
};
