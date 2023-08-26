import { theme } from "antd";
import { GlobalToken } from "antd/es/theme/interface";

export const useAntdTheme = (): GlobalToken & { colorTheme: string } => {
  const { token } = theme.useToken();
  return { ...token, colorTheme: "#2F80ED" };
};
