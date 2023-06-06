import { Injectable } from "injection-js";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { sampleFromSchema } from "@lepton-libs/open-api-tool/samples";
import type { OpenAPI, OpenAPIV3_1, OpenAPIV3 } from "openapi-types";

enum HttpMethods {
  GET = "get",
  PUT = "put",
  POST = "post",
  DELETE = "delete",
  OPTIONS = "options",
  HEAD = "head",
  PATCH = "patch",
}

export type SchemaObject = OpenAPIV3_1.SchemaObject | OpenAPIV3.SchemaObject;

type OperationWithRequestBody = Omit<OpenAPI.Operation, "requestBody"> & {
  requestBody: OpenAPIV3_1.RequestBodyObject | OpenAPIV3.RequestBodyObject;
};

export type OperationWithPath = OpenAPI.Operation<{ path: string }>;

type MediaTypeObject = OpenAPIV3_1.MediaTypeObject | OpenAPIV3.MediaTypeObject;

// TODO(hsuanxyz): support be support form-data and binary data(in formData too)
type ALLOWED_MEDIA_TYPES = "application/json";
const ALLOWED_MEDIA_TYPES: ALLOWED_MEDIA_TYPES[] = ["application/json"];

@Injectable()
export class OpenApiService {
  async parse(schema: SafeAny): Promise<OpenAPI.Document | null> {
    const resolve = await import("swagger-client/es/resolver").then(
      (m) => m.default
    );
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
  async buildRequest(
    spec: OpenAPI.Document,
    operationId: string,
    requestBody?: SafeAny
  ) {
    const buildRequest = await import("swagger-client/es/execute").then(
      (m) => m.buildRequest
    );
    return buildRequest({
      spec,
      operationId,
      requestBody,
    });
  }

  /**
   * From https://github.com/swagger-api/swagger-js/blob/master/src/execute/index.js#LL53C17-L53C24
   * Input request object, output response object.
   */
  executeRequest(_request: SafeAny) {
    // TODO
  }

  /**
   * From https://github.com/swagger-api/swagger-ui/blob/021a1d495c84ee79c4792a92c93d73aee9c4a9c2/src/core/plugins/request-snippets/fn.js#L153
   * Input request object, output curl string.
   */
  curlify(_request: SafeAny) {
    // TODO
  }
}
