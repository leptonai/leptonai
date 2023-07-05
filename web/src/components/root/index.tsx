import { UseSetupNavigate } from "@lepton-dashboard/hooks/use-setup-navigate";
import { FC, Suspense } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import styled from "@emotion/styled";
import { Loading } from "@lepton-dashboard/components/loading";
import { useSetupMonaco } from "@lepton-dashboard/hooks/use-setup-monaco";
import { useSetupNotification } from "@lepton-dashboard/hooks/use-setup-interceptor";
import { useInitialize } from "@lepton-dashboard/hooks/use-initialize";
import { useSetupEcharts } from "@lepton-dashboard/hooks/use-setup-echarts";
import { Outlet } from "react-router-dom";

const Container = styled.div`
  height: 100%;
`;
export const Root: FC = () => {
  const theme = useAntdTheme();
  useSetupMonaco();
  useSetupNotification();
  useSetupEcharts();
  UseSetupNavigate();
  const initialized = useInitialize();
  return initialized ? (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        font-family: ${theme.fontFamily};
        color: ${theme.colorText};
        font-size: ${theme.fontSize}px;
      `}
    >
      <Suspense fallback={<Loading />}>
        <Outlet />
      </Suspense>
    </Container>
  ) : (
    <Loading />
  );
};
