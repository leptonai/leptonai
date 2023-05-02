import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
const Container = styled.div`
  flex: 0 0 80px;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  font-size: 12px;
`;

const Meta = styled.div`
  display: flex;
  height: 24px;
  width: 100%;
  align-items: center;
  justify-content: space-between;
`;
export const Footer: FC = () => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        color: ${theme.colorTextHeading};
        border-top: 1px solid ${theme.colorBorderSecondary};
        color: ${theme.colorTextSecondary};
      `}
    >
      <Meta>
        <strong>VERSION</strong> <span>{__APP_VERSION__}</span>
      </Meta>
      <Meta>
        <strong>COMMIT</strong>
        <a
          css={css`
            color: ${theme.colorTextSecondary};
            text-decoration: none;
            &:hover {
              color: ${theme.colorLink};
            }
          `}
          target="_blank"
          href={`https://github.com/leptonai/dashboard/commit/${__COMMIT_HASH__}`}
          rel="noreferrer"
        >
          #{__COMMIT_HASH__}
        </a>
      </Meta>
    </Container>
  );
};
