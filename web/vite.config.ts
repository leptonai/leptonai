import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import typescript from "@rollup/plugin-typescript";
import checker from "vite-plugin-checker";
import injectionTransformer from "./libs/transformer";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    server: {
      port: 3000,
      hmr: false,
      proxy: {
        "/api/v1": {
          target: env.VITE_WORKSPACE_URL,
          changeOrigin: true,
        },
      },
    },
    test: {
      include: ["**/*.spec.{js,ts,jsx,tsx}"],
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
      checker({
        typescript: true,
      }),
    ],
  };
});
