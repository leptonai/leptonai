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
          <path
            stroke="#2D9CDB"
            fill="none"
            strokeLinejoin="round"
            strokeWidth="20"
            d="M112.1,76.3l42.8,24.7c5.3,3,8.5,8.6,8.5,14.7v49.4c0,6.1-3.2,11.7-8.5,14.7l-42.8,24.7c-5.3,3-11.7,3-17,0
		l-42.8-24.7c-5.3-3-8.5-8.6-8.5-14.7v-49.4c0-6.1,3.2-11.7,8.5-14.7l42.8-24.7C100.4,73.3,106.8,73.3,112.1,76.3z"
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
              animation: ${dash} 0.5s linear infinite;
            `}
            d="M112.1,76.3l42.8,24.7c5.3,3,8.5,8.6,8.5,14.7v49.4c0,6.1-3.2,11.7-8.5,14.7l-42.8,24.7c-5.3,3-11.7,3-17,0
		l-42.8-24.7c-5.3-3-8.5-8.6-8.5-14.7v-49.4c0-6.1,3.2-11.7,8.5-14.7l42.8-24.7C100.4,73.3,106.8,73.3,112.1,76.3z"
          />
        </g>
        <g>
          <path
            stroke="#2F80ED"
            fill="none"
            strokeLinejoin="round"
            strokeWidth="20"
            d="M188.4,79l42.8,24.7c5.3,3,8.5,8.6,8.5,14.7v49.4c0,6.1-3.2,11.7-8.5,14.7l-42.8,24.7c-5.3,3-11.7,3-17,0
		l-42.8-24.7c-5.3-3-8.5-8.6-8.5-14.7v-49.4c0-6.1,3.2-11.7,8.5-14.7L171.4,79C176.6,75.9,183.1,75.9,188.4,79z"
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
              animation: ${dash} 0.5s linear infinite;
              animation-delay: 0.25s;
            `}
            d="M188.4,79l42.8,24.7c5.3,3,8.5,8.6,8.5,14.7v49.4c0,6.1-3.2,11.7-8.5,14.7l-42.8,24.7c-5.3,3-11.7,3-17,0
		l-42.8-24.7c-5.3-3-8.5-8.6-8.5-14.7v-49.4c0-6.1,3.2-11.7,8.5-14.7L171.4,79C176.6,75.9,183.1,75.9,188.4,79z"
          />
        </g>
      </svg>
    </Container>
  );
};
