const uiConfig = require("@lepton/ui/tailwind.config");

/** @type {import('tailwindcss').Config} */
export default {
  ...uiConfig,
  content: [...uiConfig.content, "./src/**/*.{ts,tsx}"],
};
