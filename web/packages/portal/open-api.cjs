const swaggerJsdoc = require("swagger-jsdoc");
const { transfromSwagger } = require("swagger-markdown");
const fs = require("fs-extra");

const options = {
  failOnErrors: true,
  definition: {
    openapi: "2.0.0",
    info: {
      title: "Portal API",
      version: "1.0.0",
    },
  },
  apis: ["./src/pages/api/**/*.ts"],
};

const openapiSpecification = swaggerJsdoc(options);
const docs = transfromSwagger(openapiSpecification, {
  forceVersion: "2",
});

fs.ensureDirSync("./docs");
fs.writeFileSync("./docs/APIs.md", docs);
