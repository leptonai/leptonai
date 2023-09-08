const uiConfig = require("@lepton/ui/tailwind.config");

/** @type {import('tailwindcss').Config} */
module.exports = {
  ...uiConfig,
  content: [...uiConfig.content, "./src/**/*.{js,ts,jsx,tsx,mdx}"],
};
