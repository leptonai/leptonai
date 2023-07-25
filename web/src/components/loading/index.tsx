import { FC } from "react";
import { css, keyframes } from "@emotion/react";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

const Container = styled.div`
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const dash = keyframes`
  from {
    stroke-dashoffset: 1000;
  }
  to {
    stroke-dashoffset: 500;
  }
`;
export const Loading: FC = () => {
  const theme = useAntdTheme();
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        min-height: 200px;
      `}
    >
      <svg viewBox="0 0 283.46 283.46" height={50} width={50}>
        <g>
          <polygon
            stroke="#2D9CDB"
            fill="none"
            strokeLinejoin="round"
            strokeWidth="20"
            points="103.59,71.41 163.34,105.91 163.34,174.91 103.59,209.41 43.83,174.91 43.83,105.91 	"
          />
          <path
            stroke="#2F80ED"
            strokeWidth="20"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            css={css`
              stroke-dasharray: 500 100;
              stroke-dashoffset: 50;
              animation: ${dash} 0.5s ease-in infinite;
            `}
            d="M103.59,71.41l59.76,34.5v69l-59.76,34.5l-59.76-34.5v-69L103.59,71.41z"
          />
        </g>
        <g>
          <polygon
            stroke="#2F80ED"
            fill="none"
            strokeLinejoin="round"
            strokeWidth="20"
            points="179.88,74.06 239.63,108.56 239.63,177.56 179.88,212.06 120.12,177.56 120.12,108.56 	"
          />
          <path
            stroke="#2D9CDB"
            strokeWidth="20"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            css={css`
              stroke-dasharray: 500 100;
              stroke-dashoffset: 50;
              animation: ${dash} 0.5s ease-in infinite;
              animation-delay: 0.25s;
            `}
            d="M179.88,74.06l59.76,34.5v69l-59.76,34.5l-59.76-34.5v-69L179.88,74.06z"
          />
        </g>
      </svg>
    </Container>
  );
};
