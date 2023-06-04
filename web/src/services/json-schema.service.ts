import { Injectable } from "injection-js";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { JSONSchema7 } from "json-schema";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";

@Injectable()
export class JsonSchemaService {
  constructor(private openApiService: OpenApiService) {}

  getPaths(schema: SafeAny): string[] {
    const paths = Object.entries(schema?.paths || {}) as [string, SafeAny];
    return paths.map(([v]) => v);
  }
  // TODO: temporary solution, a better parsing solution is needed.
  parse(
    schema: SafeAny,
    path?: string
  ): {
    inputExample: SafeAny;
    inputSchema: JSONSchema7;
  } {
    if (path) {
      const inputRef =
        schema?.paths?.[path]?.post?.requestBody?.content?.["application/json"]
          ?.schema?.$ref || "";
      const inputSchemaName = inputRef.replace("#/components/schemas/", "");
      const inputSchema = inputSchemaName
        ? {
            ...schema.components?.schemas?.[inputSchemaName],
            components: schema.components,
          }
        : {};
      const example =
        schema?.paths?.[path]?.post?.requestBody?.content?.["application/json"]
          ?.example;
      const inputExample = this.openApiService.sampleFromSchema(
        inputSchema,
        example
      );
      return { inputExample, inputSchema };
    } else {
      return { inputExample: {}, inputSchema: {} };
    }
  }
}
