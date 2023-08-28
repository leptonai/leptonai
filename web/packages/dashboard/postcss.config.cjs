const uiConfig = require("@lepton/ui/postcss.config");

module.exports = {
  ...uiConfig,
  plugins: {
    ...uiConfig.plugins,
    'postcss-antd-fixes': {}
  }
};
