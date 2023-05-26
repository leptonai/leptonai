import { FC, PropsWithChildren } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import styled from "@emotion/styled";
import { Loading } from "@lepton-dashboard/components/loading";
import { useSetupMonaco } from "@lepton-dashboard/hooks/use-setup-monaco";
import { useSetupInterceptor } from "@lepton-dashboard/hooks/use-setup-interceptor";
import { useInitialize } from "@lepton-dashboard/hooks/use-initialize";
import { useSetupEcharts } from "@lepton-dashboard/hooks/use-setup-echarts";

const Container = styled.div`
  height: 100%;
`;
export const Root: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  useSetupMonaco();
  useSetupInterceptor();
  useSetupEcharts();
  const initialized = useInitialize();
  return initialized ? (
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
  ) : (
    <Loading />
  );
};
