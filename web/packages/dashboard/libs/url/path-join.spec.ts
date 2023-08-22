import { expect, test, describe } from "vitest";
import { pathJoin } from "./path-join";

describe("pathJoin", () => {
  test("should be join path", () => {
    expect(pathJoin("https://example.com", "foo", "bar")).toBe(
      "https://example.com/foo/bar"
    );

    expect(pathJoin("foo", "bar")).toBe("foo/bar");
  });

  test("should be join path with empty string", () => {
    expect(pathJoin("https://example.com", "", "foo", "bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("foo", "", "bar")).toBe("foo/bar");
  });

  test("should be join path with pathname in base", () => {
    expect(pathJoin("https://example.com/foo", "bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("bar")).toBe("bar");
  });

  test("should be join path with pathname in base and empty string", () => {
    expect(pathJoin("https://example.com/foo", "", "bar")).toBe(
      "https://example.com/foo/bar"
    );
  });

  test("should be join path with extra slash in base", () => {
    expect(pathJoin("https://example.com/foo/", "bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("https://example.com//", "/foo/bar/")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("/foo/", "/bar")).toBe("foo/bar");
  });

  test("should be join path with slash in urls", () => {
    expect(pathJoin("https://example.com/", "foo/bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("https://example.com/", "/foo/bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("https://example.com", "/foo", "/bar")).toBe(
      "https://example.com/foo/bar"
    );
    expect(pathJoin("/foo", "/bar", "/baz")).toBe("foo/bar/baz");
  });
});
