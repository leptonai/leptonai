declare module "swagger-client/es/resolver";

declare module "swagger-client/es/execute" {
  import type { OpenAPIRequest } from "@lepton-libs/open-api-tool";
  import type { OpenAPI } from "openapi-types";
  interface RequestOptions {
    spec: OpenAPI.Document;
    operationId: string;
    requestBody?: unknown;
    parameters?: Record<string, unknown>;
    responseContentType?:
      | "application/json"
      | "multipart/form-data"
      | "application/x-www-form-urlencoded"
      | "application/octet-stream";
    server?: string;
    serverVariables?: {
      version?: string;
    };
    securities?: {
      authorized?: {
        BearerAuth?: string;
        ApiKey?: string;
        BasicAuth?: string;
        oAuth2?: string;
      };
    };
  }

  export type ExecuteRequestOptions = RequestOptions & {
    pathName?: string;
    method?: string;
  };

  export function buildRequest(
    options: RequestOptions
  ): Promise<OpenAPIRequest>;

  export function execute<T>(options: ExecuteRequestOptions): Promise<T>;
}
