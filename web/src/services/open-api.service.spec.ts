import { describe, beforeAll, test, expect } from "vitest";
import {
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
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

  describe("generate Python code", () => {
    test("should generate Python code", async () => {
      const body = {
        texts: "string",
      };
      const code = service.toPythonSDKCode(
        {
          request: { body },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code.replace(/\t/g, "  "))
        .toEqual(`from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example(
  texts="string"
)

print(result)`);
    });

    test("should generate Python code with empty body", async () => {
      const code = service.toPythonSDKCode(
        {
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      const code2 = service.toPythonSDKCode(
        {
          request: {
            body: {},
          },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code).toEqual(code2);

      expect(code).toEqual(
        `from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example()

print(result)`
      );
    });

    test("should generate Python code with url", async () => {
      const code = service.toPythonSDKCode(
        {
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        "https://latest.cloud.lepton.ai"
      );

      expect(code.replace(/\t/g, "  ")).toEqual(
        `from leptonai.client import Client

client = Client("https://latest.cloud.lepton.ai", token="$YOUR_TOKEN")
result = client.example()

print(result)`
      );
    });

    test("should generate Python code with boolean", async () => {
      const body = {
        boolean: true,
      };
      const code = service.toPythonSDKCode(
        {
          request: { body },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code.replace(/\t/g, "  ")).toEqual(
        `from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example(
  boolean=True
)

print(result)`
      );
    });

    test("should generate Python code with null", async () => {
      const body = {
        use_null: null,
      };
      const code = service.toPythonSDKCode(
        {
          request: { body },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code.replace(/\t/g, "  "))
        .toEqual(`from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example(
  use_null=None
)

print(result)`);
    });

    test("should generate Python code with object value", async () => {
      const body = {
        object: {
          test: 1,
          object: {
            string: "string",
            number: 1,
          },
        },
        number: 1,
      };
      const code = service.toPythonSDKCode(
        {
          request: { body },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code.replace(/\t/g, "  "))
        .toEqual(`from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example(
  object={
    "test": 1,
    "object": {
      "string": "string",
      "number": 1
    }
  },
  number=1
)

print(result)`);
    });

    test("should generate Python code with array value", async () => {
      const body = {
        array: ["1", "2"],
        arrayNumber: [1, 2],
        arrayObject: [
          {
            test: 1,
          },
          {
            test: 2,
          },
        ],
        number: 1,
      };
      const code = service.toPythonSDKCode(
        {
          request: { body },
          operation: {
            path: "/example",
          },
        } as unknown as LeptonAPIItem,
        {
          workspace: "workspace",
          deployment: "test",
        }
      );

      expect(code.replace(/\t/g, "  ")).toEqual(
        `from leptonai.client import Client

client = Client("workspace", "test", token="$YOUR_TOKEN")
result = client.example(
  array=[
    "1",
    "2"
  ],
  arrayNumber=[
    1,
    2
  ],
  arrayObject=[
    {
      "test": 1
    },
    {
      "test": 2
    }
  ],
  number=1
)

print(result)`
      );
    });
  });
});
