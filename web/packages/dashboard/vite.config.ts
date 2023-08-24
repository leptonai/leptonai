import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import typescript from "@rollup/plugin-typescript";
import checker from "vite-plugin-checker";
import injectionTransformer from "./libs/transformer";
import { viteStaticCopy } from "vite-plugin-static-copy";
import prerender from "@prerenderer/rollup-plugin";

const skipPreRender = process.env.SKIP_PRERENDER;
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    preview: {
      port: 3001,
      host: "0.0.0.0",
      hmr: false,
      proxy: {
        "/api/v1": {
          target: "https://y90kazsl.app.lepton.ai",
          changeOrigin: true,
        },
        "/run": {
          target: "https://y90kazsl.app.lepton.ai",
          changeOrigin: true,
        },
      },
    },
    server: {
      port: 3000,
      host: "0.0.0.0",
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
      viteStaticCopy({
        targets: [
          {
            src: "node_modules/shiki/dist/onig.wasm",
            dest: "shiki/dist",
          },
          {
            src: "node_modules/shiki/themes/github-dark.json",
            dest: "shiki/themes",
          },
          {
            src: "node_modules/shiki/themes/github-light.json",
            dest: "shiki/themes",
          },
          {
            src: "node_modules/shiki/languages/shellscript.tmLanguage.json",
            dest: "shiki/languages",
          },
          {
            src: "node_modules/shiki/languages/python.tmLanguage.json",
            dest: "shiki/languages",
          },
          {
            src: "node_modules/shiki/languages/json.tmLanguage.json",
            dest: "shiki/languages",
          },
        ],
      }),
      skipPreRender
        ? null
        : prerender({
            routes: ["/playground/llama2", "/playground/sdxl"],
            rendererOptions: {
              renderAfterTime: 5000,
              inject: true,
            },
          }),
    ],
  };
});
