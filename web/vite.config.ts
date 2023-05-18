import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import typescript from "@rollup/plugin-typescript";
import injectionTransformer from "./libs/transformer";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const __PROXY_URL__ = process.env.PROXY_URL || env.PROXY_URL || "";
  const __CLUSTER_URL__ = process.env.__CLUSTER_URL__ || env.CLUSTER_URL || "";

  return {
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
      __PROXY_URL__: JSON.stringify(__PROXY_URL__),
      __CLUSTER_URL__: JSON.stringify(__CLUSTER_URL__),
    },
    server: {
      port: 3000,
      hmr: false,
      proxy: {
        [__PROXY_URL__]: {
          target: `http://${__CLUSTER_URL__}`,
          changeOrigin: true,
          rewrite: (path) => {
            return path.replace(__PROXY_URL__, "").replace(__CLUSTER_URL__, "");
          },
        },
        "/run": {
          target: `http://k8s-default-gpt2ingr-194cbacd01-1823409343.us-east-1.elb.amazonaws.com`,
          changeOrigin: true,
        },
      },
    },
    plugins: [
      typescript({
        transformers: {
          before: [
            {
              type: "program",
              factory: (program) => injectionTransformer(program),
            },
          ],
        },
      }),
      tsconfigPaths(),
      react({
        jsxImportSource: "@emotion/react",
        babel: {
          plugins: ["@emotion/babel-plugin"],
        },
      }),
    ],
  };
});
