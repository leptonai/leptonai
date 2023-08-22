import { defineConfig } from "cypress";
import { loadEnv } from "vite";
import viteConfig from "./vite.config";

const env = loadEnv("e2e", process.cwd(), "");

export default defineConfig({
  video: false,
  watchForFileChanges: false,
  component: {
    devServer: {
      framework: "react",
      bundler: "vite",
      viteConfig: {
        ...viteConfig,
      },
    },
  },
  e2e: {
    specPattern: ["cypress/**/*.spec.{js,ts,jsx,tsx}"],
    setupNodeEvents(on, config) {
      config.env.token =
        process.env.CI_WORKSPACE_TOKEN || env.CI_WORKSPACE_TOKEN;
      return config;
    },
  },
});
