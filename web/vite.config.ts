import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import typescript from "@rollup/plugin-typescript";
import injectionTransformer from "./libs/transformer";
import { execSync } from "child_process";
const commitHash = execSync("git rev-parse --short HEAD").toString();

export default defineConfig({
  define: {
    __COMMIT_HASH__: JSON.stringify(commitHash),
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  server: {
    port: 3000,
    hmr: false,
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
});
