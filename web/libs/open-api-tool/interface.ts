type JSONPrimitive = string | number | boolean | null;
type JSONObject = { [key: string]: JSONValue };
type JSONArray = JSONValue[];
type JSONValue = JSONPrimitive | JSONObject | JSONArray;
type JSONObjectOrArray = JSONObject | JSONArray;

export interface OpenAPIRequest {
  body: JSONObjectOrArray | File | null | string;
  headers: { [key: string]: string };
  curlOptions?: string[];
  method: string;
  url: string;
}

export type RequestWithObjectBody = OpenAPIRequest & {
  body: JSONObjectOrArray;
};
