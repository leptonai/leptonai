import { FC, ReactNode } from "react";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

const Container = styled.div`
  height: 32px;
  display: flex;
  align-items: center;
`;
const Key = styled.div`
  height: 100%;
  display: flex;
  margin-right: 8px;
  align-items: center;
`;
const Value = styled.div`
  height: 100%;
  display: flex;
  align-items: center;
`;
export const KeyValue: FC<{ title?: ReactNode; value: ReactNode }> = ({
  title,
  value,
}) => {
  const theme = useAntdTheme();
  return (
    <Container>
      {title && (
        <Key
          css={css`
            color: ${theme.colorTextTertiary};
          `}
        >
          {title} :
        </Key>
      )}
      <Value
        css={css`
          color: ${theme.colorText};
        `}
      >
        {value}
      </Value>
    </Container>
  );
};
