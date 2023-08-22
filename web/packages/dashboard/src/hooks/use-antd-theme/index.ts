import { theme } from "antd";

export const useAntdTheme = () => {
  const { token } = theme.useToken();
  return { ...token, colorTheme: "#2F80ED" };
};
