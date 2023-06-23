import { ReactNode, useEffect } from "react";
import axios, { AxiosError, CanceledError } from "axios";
import { App } from "antd";

interface LeptonError {
  code: string;
  message: string;
}

export const useSetupInterceptor = () => {
  const { notification } = App.useApp();

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error: AxiosError<LeptonError>) => {
        if (error instanceof CanceledError) {
          return Promise.reject(error);
        }

        /**
         * This error will be caught and handled by the {@link AppInterceptor#intercept} method.
         */
        if (error?.status === 401 || error.response?.status === 401) {
          return Promise.reject(error);
        }

        const requestId = error.response?.headers?.["x-request-id"];
        const message: ReactNode = error.response?.data?.code || error.code;
        let description: ReactNode =
          error.response?.data?.message || error.message;
        description = requestId ? (
          <>
            <strong>Error Message</strong>: {description}
            <br />
            <strong>Request ID</strong>: {requestId}
            <br />
            <strong>Timestamp</strong>: {new Date().toLocaleString()}
          </>
        ) : (
          description
        );
        notification.error({
          message,
          description,
        });
        return Promise.reject(error);
      }
    );
    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, [notification]);
};
