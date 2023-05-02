import { theme } from "antd";

export const useAntdTheme = () => {
  const { token } = theme.useToken();
  return token;
};
