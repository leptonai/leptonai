import { FC, PropsWithChildren, useEffect } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import styled from "@emotion/styled";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { useLocation } from "react-router-dom";
import { InitializerService } from "@lepton-dashboard/services/initializer.service.ts";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { App } from "antd";
import axios from "axios";
import { Loading } from "@lepton-dashboard/components/loading";

const Container = styled.div`
  height: 100%;
`;
export const Root: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  const { notification } = App.useApp();
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      function (response) {
        return response;
      },
      function (error) {
        if (error.response?.data?.message) {
          const message = error.response.data.message;
          const firstLetter = message.charAt(0);
          const firstLetterCap = firstLetter.toUpperCase();
          const remainingLetters = message.slice(1);
          const capitalizedMessage = firstLetterCap + remainingLetters;
          notification.error({
            message: capitalizedMessage,
            description: error.response.data.error,
          });
        } else {
          notification.error({
            message: error.code,
            description: error.message,
          });
        }

        return Promise.reject(error);
      }
    );
    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, [notification]);
  const refreshService = useInject(RefreshService);
  const location = useLocation();
  useEffect(() => {
    refreshService.integrateWithRouter(location.pathname);
  }, [location.pathname, refreshService]);
  const initializerService = useInject(InitializerService);
  const initialized = useStateFromBehaviorSubject(
    initializerService.initialized$
  );
  useEffect(() => {
    initializerService.bootstrap();
  }, [initializerService]);
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
