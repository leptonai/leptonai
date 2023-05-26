import { useEffect } from "react";
import axios from "axios";
import { App } from "antd";

export const useSetupInterceptor = () => {
  const { notification } = App.useApp();

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      function (response) {
        return response;
      },
      function (error) {
        if (error.response?.data?.message) {
          const message = error.response.data.code;
          notification.error({
            message,
            description: error.response.data.message,
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
};
