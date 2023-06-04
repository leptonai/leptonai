import { expect, test } from "vitest";
import { sampleFromSchema } from "@lepton-libs/open-api-tool/samples";

const schema = {
  components: {
    schemas: {
      default: {
        properties: {
          do_sample: {
            default: true,
            title: "Do Sample",
            type: "boolean",
          },
          inputs: {
            items: {
              type: "string",
            },
            type: "array",
            title: "Inputs",
          },
          max_new_tokens: {
            title: "Max New Tokens",
            type: "integer",
          },
          max_time: {
            title: "Max Time",
            type: "number",
          },
          num_return_sequences: {
            default: 1,
            title: "Num Return Sequences",
            type: "integer",
          },
          repetition_penalty: {
            title: "Repetition Penalty",
            type: "number",
          },
          return_full_text: {
            default: true,
            title: "Return Full Text",
            type: "boolean",
          },
          temperature: {
            default: 1,
            title: "Temperature",
            type: "number",
          },
          top_k: {
            title: "Top K",
            type: "integer",
          },
          top_p: {
            title: "Top P",
            type: "number",
          },
        },
        required: ["inputs"],
        title: "RunInput",
        type: "object",
      },
      defaultWithExample: {
        example: {
          do_sample: true,
          inputs: ["I enjoy walking with my cute dog"],
          max_length: 50,
          top_k: 50,
          top_p: 0.95,
        },
        schema: {
          $ref: "#/components/schemas/default",
        },
      },
      withoutDefault: {
        properties: {
          x: {
            title: "X",
            type: "integer",
          },
        },
        required: ["x"],
        title: "default",
        type: "object",
      },
    },
  },
  info: {
    title: "samples-test",
    version: "0.1.0",
  },
  openapi: "3.0.2",
};

test("should generate sample from schema without default", () => {
  const sample = sampleFromSchema(schema.components.schemas.withoutDefault, {});
  expect(sample).toEqual({ x: 0 });
});

test("should generate sample from schema with default", () => {
  const sample = sampleFromSchema(schema.components.schemas.default, {});
  expect(sample).toEqual({
    do_sample: true,
    inputs: ["string"],
    max_new_tokens: 0,
    max_time: 0,
    num_return_sequences: 1,
    repetition_penalty: 0,
    return_full_text: true,
    temperature: 1,
    top_k: 0,
    top_p: 0,
  });
});

test("should generate sample from schema with example", () => {
  const sample = sampleFromSchema(
    schema.components.schemas.defaultWithExample,
    {}
  );
  expect(sample).toEqual({
    do_sample: true,
    inputs: ["I enjoy walking with my cute dog"],
    max_length: 50,
    top_k: 50,
    top_p: 0.95,
  });
});

test("should generate sample from schema with example override", () => {
  const sample = sampleFromSchema(
    schema.components.schemas.defaultWithExample,
    {},
    {
      inputs: ["I enjoy walking with my cute dog"],
    }
  );
  expect(sample).toEqual({
    inputs: ["I enjoy walking with my cute dog"],
  });
});
