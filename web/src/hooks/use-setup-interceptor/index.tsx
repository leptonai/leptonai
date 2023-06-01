import { useEffect } from "react";
import axios from "axios";
import { App } from "antd";

export const useSetupInterceptor = () => {
  const { notification } = App.useApp();

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        const requestId = error.response.headers?.["x-request-id"];
        const message = error.response?.data?.code || error.code;
        let description = error.response?.data?.message || error.message;
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
