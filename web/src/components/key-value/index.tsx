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
  flex: 0 0 auto;
  overflow: hidden;
`;
const Value = styled.div`
  height: 100%;
  display: flex;
  align-items: center;
  flex: 1 1 auto;
  overflow: hidden;
`;
const Ellipsis = styled.div`
  width: 100%;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
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
            white-space: nowrap;
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
        <Ellipsis>{value}</Ellipsis>
      </Value>
    </Container>
  );
};
