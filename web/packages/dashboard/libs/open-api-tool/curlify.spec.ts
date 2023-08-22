import { expect, test, describe } from "vitest";
import { curlBash as curl } from "./curlify";
import { OpenAPIRequest } from "./interface";

describe("curlify", () => {
  test("should be generate curl command from request object", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "GET",
      headers: {
        accept: "application/json",
      },
      body: null,
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'GET' \\
  'https://example.com' \\
  -H 'accept: application/json'`);
  });

  test("should be generate curl command from request object with body", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: {
        name: "John Doe",
        age: 30,
      },
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'POST' \\
  'https://example.com' \\
  -H 'accept: application/json' \\
  -H 'content-type: application/json' \\
  -d '${JSON.stringify(request.body, null, 2)}'`);
  });

  test("should be generate curl command from request object with string body", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        name: "John Doe",
        age: 30,
      }),
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'POST' \\
  'https://example.com' \\
  -H 'accept: application/json' \\
  -H 'content-type: application/json' \\
  -d '${request.body}'`);
  });

  test("should be generate curl command from request object with formData", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "multipart/form-data",
      },
      body: {
        name: "John Doe",
        age: 30,
      },
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'POST' \\
  'https://example.com' \\
  -H 'accept: application/json' \\
  -H 'content-type: multipart/form-data' \\
  -F 'name=John Doe' \\
  -F 'age=30'`);
  });

  test("should be generate curl command from request object with no body", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: null,
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'POST' \\
  'https://example.com' \\
  -H 'accept: application/json' \\
  -H 'content-type: application/json' \\
  -d ''`);
  });

  test("should be generate curl command from request object with query params in url", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com?name=John",
      method: "GET",
      headers: {
        accept: "application/json",
      },
      body: null,
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'GET' \\
  'https://example.com?name=John' \\
  -H 'accept: application/json'`);
  });

  test("should be generate curl command from request object with array of query params in url", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com?name=John|Doe",
      method: "GET",
      headers: {
        accept: "application/json",
      },
      body: null,
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'GET' \\
  'https://example.com?name=John|Doe' \\
  -H 'accept: application/json'`);
  });

  test("should be generate curl command from request object with auth in header", () => {
    const request: OpenAPIRequest = {
      url: "https://example.com",
      method: "GET",
      headers: {
        accept: "application/json",
        authorization: "Basic YWxhZGRpbjpvc==",
      },
      body: null,
    };
    const result = curl(request);
    expect(result).toBe(`curl -X 'GET' \\
  'https://example.com' \\
  -H 'accept: application/json' \\
  -H 'authorization: Basic YWxhZGRpbjpvc=='`);
  });
});
