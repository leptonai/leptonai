import { Injectable } from "injection-js";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { JSONSchema7 } from "json-schema";

@Injectable()
export class JsonSchemaService {
  // TODO: temporary solution, a better parsing solution is needed.
  parse(schema: SafeAny): {
    path?: string;
    inputExample: SafeAny;
    inputSchema: JSONSchema7;
  } {
    const paths = Object.entries(schema?.paths || {}) as SafeAny;
    const path = paths[0]?.[0];
    const inputRef =
      paths[0]?.[1]?.post?.requestBody?.content?.["application/json"]?.schema
        ?.$ref || "";
    const inputSchemaName = inputRef.replace("#/components/schemas/", "");
    const inputSchema = inputSchemaName
      ? schema.components?.schemas?.[inputSchemaName]
      : {};
    const inputExample =
      paths[0]?.[1]?.post?.requestBody?.content?.["application/json"]?.example;
    return { path, inputExample, inputSchema };
  }
}
