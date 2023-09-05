const uiConfig = require("@lepton/ui/tailwind.config");
const playgroundConfig = require("@lepton/playground/tailwind.config");

/** @type {import('tailwindcss').Config} */
export default {
  ...uiConfig,
  content: [
    ...uiConfig.content,
    ...playgroundConfig.content,
    "./src/**/*.{ts,tsx}",
    "./libs/**/*.{ts,tsx}",
  ],
};
