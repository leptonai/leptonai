import { defineConfig } from "cypress";
import viteConfig from "./vite.config";

export default defineConfig({
  video: false,
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
    specPattern: "cypress/**/*.spec.{js,ts,jsx,tsx}",
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
