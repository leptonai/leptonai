type JSONPrimitive = string | number | boolean | null;
type JSONObject = { [key: string]: JSONValue };
type JSONArray = JSONValue[];
type JSONValue = JSONPrimitive | JSONObject | JSONArray;
type JSONObjectOrArray = JSONObject | JSONArray;

export enum HttpMethods {
  GET = "get",
  PUT = "put",
  POST = "post",
  DELETE = "delete",
  OPTIONS = "options",
  HEAD = "head",
  PATCH = "patch",
}

export interface OpenAPIRequest {
  body: JSONObjectOrArray | File | null | string;
  headers: { [key: string]: string };
  curlOptions?: string[];
  method: HttpMethods | string;
  url: string;
}

export type RequestWithObjectBody = OpenAPIRequest & {
  body: JSONObjectOrArray;
};
