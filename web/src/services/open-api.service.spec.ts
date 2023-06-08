import { describe, beforeAll, test, expect } from "vitest";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
import { OpenAPIV3 } from "openapi-types";

const generateSpec = ({
  paths,
}: {
  paths: OpenAPIV3.Document["paths"];
}): OpenAPIV3.Document => {
  return {
    openapi: "3.0.0",
    info: {
      title: "test",
      version: "1.0.0",
    },
    paths,
  } as OpenAPIV3.Document;
};

describe("open-api.service", () => {
  let service: OpenApiService;
  beforeAll(() => {
    service = new OpenApiService();
  });

  describe("buildRequest", () => {
    test("should build request", async () => {
      const spec = generateSpec({
        paths: {
          example: {
            get: {
              operationId: "example",
              responses: {},
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", undefined);

      expect(request).toEqual({
        method: "GET",
        url: "example",
        credentials: "same-origin",
        headers: {},
      });
    });

    test("should build request with query", async () => {
      const spec = generateSpec({
        paths: {
          example: {
            get: {
              operationId: "example",
              responses: {},
              parameters: [
                {
                  name: "test",
                  in: "query",
                  schema: {
                    type: "string",
                  },
                },
              ],
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", null, {
        test: "test",
      });

      expect(request).toEqual({
        method: "GET",
        url: "example?test=test",
        credentials: "same-origin",
        headers: {},
      });
    });

    test("should build request with body", async () => {
      const spec = generateSpec({
        paths: {
          example: {
            post: {
              operationId: "example",
              responses: {},
              requestBody: {
                content: {
                  "application/json": {
                    schema: {
                      type: "object",
                      properties: {
                        test: {
                          type: "string",
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", {
        test: "in-body",
      });

      expect(request).toEqual({
        method: "POST",
        url: "example",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
        },
        body: {
          test: "in-body",
        },
      });
    });

    test("should build request with urlencoded form data", async () => {
      const spec = generateSpec({
        paths: {
          example: {
            post: {
              operationId: "example",
              responses: {},
              requestBody: {
                content: {
                  "application/x-www-form-urlencoded": {
                    schema: {
                      type: "object",
                      properties: {
                        test: {
                          type: "string",
                        },
                        number: {
                          type: "number",
                        },
                        array: {
                          type: "array",
                          items: {
                            type: "string",
                          },
                        },
                        object: {
                          type: "object",
                          properties: {
                            test: {
                              type: "number",
                            },
                          },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", {
        test: "in-from-data",
        number: 1,
        array: ["1", "2"],
        object: {
          test: 1,
        },
      });

      expect(request).toEqual({
        method: "POST",
        url: "example",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "test=in-from-data&number=1&array=1,2&object=%7B%22test%22%3A1%7D",
      });
    });

    test("should build request with parameters in path", async () => {
      const spec = generateSpec({
        paths: {
          "example/{test}": {
            get: {
              operationId: "example",
              responses: {},
              parameters: [
                {
                  name: "test",
                  in: "path",
                  schema: {
                    type: "string",
                  },
                },
              ],
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", null, {
        test: "in-path",
      });

      expect(request).toEqual({
        method: "GET",
        url: "example/in-path",
        credentials: "same-origin",
        headers: {},
      });
    });

    test("should build request with parameters in header", async () => {
      const spec = generateSpec({
        paths: {
          example: {
            get: {
              operationId: "example",
              responses: {},
              parameters: [
                {
                  name: "test",
                  in: "header",
                  schema: {
                    type: "string",
                  },
                },
              ],
            },
          },
        },
      });

      const request = await service.buildRequest(spec, "example", null, {
        test: "in-header",
      });

      expect(request).toEqual({
        method: "GET",
        url: "example",
        credentials: "same-origin",
        headers: {
          test: "in-header",
        },
      });
    });
  });
});
