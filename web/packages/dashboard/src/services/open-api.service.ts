import { Injectable } from "injection-js";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { buildRequest } from "swagger-client/es/execute";
import resolve from "swagger-client/es/resolver";
import type { OpenAPI, OpenAPIV3_1, OpenAPIV3 } from "openapi-types";
import {
  sampleFromSchema,
  curlBash,
  OpenAPIRequest,
  HttpMethods,
} from "@lepton-libs/open-api-tool";

export type SchemaObject = OpenAPIV3_1.SchemaObject | OpenAPIV3.SchemaObject;
type ArraySchemaObject =
  | OpenAPIV3.ArraySchemaObject
  | OpenAPIV3_1.ArraySchemaObject;
type OperationWithRequestBody = Omit<OpenAPI.Operation, "requestBody"> & {
  requestBody: OpenAPIV3_1.RequestBodyObject | OpenAPIV3.RequestBodyObject;
};

export type OperationWithPath = OpenAPI.Operation<{ path: string }>;

type MediaTypeObject = OpenAPIV3_1.MediaTypeObject | OpenAPIV3.MediaTypeObject;

type ALLOWED_MEDIA_TYPES = "application/json" | "multipart/form-data";
// TODO(hsuanxyz): support be support binary data
const ALLOWED_MEDIA_TYPES = [
  "application/json",
  "multipart/form-data",
] as const;

export interface LeptonAPIItem {
  operationId: string;
  operation: OperationWithPath;
  request: OpenAPIRequest | null;
  schema: SchemaObject | null;
}

@Injectable()
export class OpenApiService {
  async parse(schema: SafeAny): Promise<OpenAPI.Document | null> {
    const resolved = await resolve({
      spec: schema,
    });
    if (resolved.errors?.length) {
      console.error(resolved.errors);
      return null;
    } else {
      return resolved.spec as OpenAPI.Document;
    }
  }

  convertToLeptonAPIItems(resolvedSchema: OpenAPI.Document): LeptonAPIItem[] {
    const operations = this.listOperations(resolvedSchema);
    const apiItems = operations
      .filter((operation) => operation.operationId)
      .map((operation) => {
        const contents = this.listMediaTypeObjects(operation);
        let requestBody: OpenAPIRequest["body"] = null;
        let schema: SchemaObject | null = null;
        let request: OpenAPIRequest | null = null;
        if (contents["application/json"]) {
          requestBody = this.sampleFromSchema(
            contents["application/json"].schema,
            contents["application/json"].example
          );
          schema =
            (contents["application/json"].schema as SchemaObject) || null;
        } else if (contents["multipart/form-data"]) {
          requestBody = this.sampleFromSchema(
            contents["multipart/form-data"].schema,
            contents["multipart/form-data"].example
          );
          schema =
            (contents["multipart/form-data"].schema as SchemaObject) || null;
        }
        this.normalizeSchema(schema);
        request = this.buildRequest(
          resolvedSchema,
          operation.operationId!,
          requestBody
        );
        return {
          operationId: operation.operationId!,
          operation,
          request,
          schema,
        };
      });

    return apiItems;
  }

  listOperations(schema: OpenAPI.Document): OperationWithPath[] {
    const operations: OperationWithPath[] = [];
    for (const path in schema.paths) {
      for (const method in schema.paths[path]) {
        if (method !== "trace" && schema.paths[path]) {
          const operation = schema.paths[path]![method as HttpMethods];
          if (operation) {
            operations.push({
              ...operation,
              path,
            });
          }
        }
      }
    }
    return operations;
  }

  hasRequestBody(operation: OpenAPI.Operation): boolean {
    return (operation as OperationWithRequestBody).requestBody !== undefined;
  }

  listMediaTypeObjects(operation: OpenAPI.Operation): {
    [type: string]: MediaTypeObject;
  } {
    const mediaTypeObjects: {
      [type in ALLOWED_MEDIA_TYPES]?: MediaTypeObject;
    } = {};
    if (this.hasRequestBody(operation)) {
      const requestBody = (operation as OperationWithRequestBody).requestBody;
      for (const mediaType in requestBody.content) {
        if (
          requestBody.content[mediaType] &&
          ALLOWED_MEDIA_TYPES.includes(mediaType as ALLOWED_MEDIA_TYPES)
        ) {
          mediaTypeObjects[mediaType as ALLOWED_MEDIA_TYPES] = requestBody
            .content[mediaType] as MediaTypeObject;
        }
      }
    }
    return mediaTypeObjects;
  }

  sampleFromSchema(schema: SafeAny, override?: SafeAny) {
    try {
      return sampleFromSchema(schema, {}, override);
    } catch (e) {
      console.error(e);
      return {};
    }
  }

  /**
   * From https://github.com/swagger-api/swagger-js/blob/63cced01d4d8d1e47ccd19010ef972fd6dc2bfad/src/execute/index.js#L249
   * Input Swagger, OpenAPI 2-3 and operationId, output request object.
   */
  buildRequest(
    spec: OpenAPI.Document,
    operationId: string,
    requestBody?: SafeAny,
    parameters?: SafeAny
  ) {
    return buildRequest({
      spec,
      operationId,
      requestBody,
      parameters,
    });
  }

  curlify(request: OpenAPIRequest) {
    try {
      return curlBash(request);
    } catch (e) {
      console.error(e);
      return "";
    }
  }

  toPythonSDKCode(
    api: LeptonAPIItem,
    scopeOrURL: { workspace: string; deployment: string } | string
  ) {
    const method = api.operation.path.replace(/^\//, "").split("/")[0];
    const hasArgs =
      api.request?.body &&
      typeof api.request.body === "object" &&
      Object.keys(api.request.body).length > 0;
    const lines = [];
    if (typeof scopeOrURL === "string") {
      lines.push(`client = Client("${scopeOrURL}", token=LEPTON_API_TOKEN)\n`);
    } else {
      lines.push(
        `client = Client("${scopeOrURL.workspace}", "${scopeOrURL.deployment}", token=LEPTON_API_TOKEN)\n`
      );
    }

    lines.push(
      `result = client.${method}${
        hasArgs
          ? `(\n${this.objectToPythonNamedArgs(api.request!.body, 1)}\n)`
          : "()"
      }\n`
    );
    lines.push("print(result)");
    return lines.join("\n");
  }

  private normalizeSchema(schema: SchemaObject | null) {
    const visit = (
      schema: SchemaObject | null,
      visitor: (item: SchemaObject) => void
    ) => {
      if (!schema) {
        return;
      }
      if (!schema.oneOf || !schema.anyOf || !schema.allOf) {
        if (schema.properties) {
          for (const key in schema.properties) {
            visit(schema.properties[key] as SchemaObject, visitor);
          }
        } else if ((schema as ArraySchemaObject).items) {
          const items = (schema as unknown as ArraySchemaObject).items;
          visit(items as SchemaObject, visitor);
        }
      }

      if (Array.isArray(schema.oneOf)) {
        schema.oneOf.forEach((item) => {
          visit(item as SchemaObject, visitor);
        });
      } else if (Array.isArray(schema.anyOf)) {
        schema.anyOf.forEach((item) => {
          visit(item as SchemaObject, visitor);
        });
      } else if (Array.isArray(schema.allOf)) {
        schema.allOf.forEach((item) => {
          visit(item as SchemaObject, visitor);
        });
      }

      visitor(schema);
    };

    visit(schema, (item) => {
      const arrayKeys = ["oneOf", "anyOf", "allOf"] as const;

      arrayKeys.forEach((key) => {
        if (Array.isArray(item[key])) {
          const types = item[key]!.map((e) => (e as SchemaObject).type);
          if (item.type && types.includes(item.type)) {
            delete item.type;
          }
          (item[key] as SchemaObject[])!.forEach((e) => {
            if (e.type && !e.title) {
              e.title = `${e.type}`;
            }
          });
        }
      });

      if (
        Object.hasOwn(item, "default") &&
        !item.type &&
        !item.anyOf &&
        !item.oneOf &&
        !item.allOf
      ) {
        const type = typeof item.default;
        switch (type) {
          case "string":
            item.type = "string";
            break;
          case "number":
            item.type = "number";
            break;
          case "boolean":
            item.type = "boolean";
            break;
          default:
            break;
        }
      }
    });
  }

  private objectToPythonNamedArgs(obj: SafeAny, indent = 0) {
    const lines = [];
    const args: string[] = [];
    for (const key in obj) {
      const value = obj[key];
      const valueStr = this.valueToPythonValue(value, indent);
      args.push(`${"  ".repeat(indent)}${key}=${valueStr}`);
    }
    lines.push(args.join(",\n"));
    return lines.join("\n");
  }

  private objectToPythonDict(obj: Record<string, unknown>, indent = 0) {
    const lines: string[] = [];
    const values: string[] = [];
    lines.push("{");
    for (const key in obj) {
      const value = obj[key];
      const valueStr = this.valueToPythonValue(value, indent + 1);
      values.push(`${"  ".repeat(indent + 1)}"${key}": ${valueStr}`);
    }
    lines.push(values.join(",\n"));
    lines.push("  ".repeat(indent) + "}");
    return lines.join("\n");
  }

  private arrayToPythonList(arr: unknown[], indent = 0) {
    const lines: string[] = [];
    const values: string[] = [];
    lines.push("[");
    for (const value of arr) {
      const valueStr = this.valueToPythonValue(value, indent + 1);
      values.push(`${"  ".repeat(indent + 1)}${valueStr}`);
    }
    lines.push(values.join(",\n"));
    lines.push("  ".repeat(indent) + "]");
    return lines.join("\n");
  }

  private valueToPythonValue(value: SafeAny, indent = 0) {
    let result = "";
    const jsType = typeof value;
    switch (jsType) {
      case "string":
        result = `${JSON.stringify(value)}`;
        break;
      case "number":
        result = `${value}`;
        break;
      case "boolean":
        result = value ? "True" : "False";
        break;
      case "object":
        if (value === null) {
          result = "None";
        } else if (Array.isArray(value)) {
          result = this.arrayToPythonList(value, indent);
        } else {
          result = this.objectToPythonDict(value, indent);
        }
    }
    return result;
  }
}
