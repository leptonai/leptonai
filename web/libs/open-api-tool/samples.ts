// Rewritten from: https://github.com/swagger-api/swagger-ui/blob/master/src/core/plugins/samples/fn.js
// Input schema object, output example object.

import RandExp from "randexp";
import type { JSONSchema7, JSONSchema7TypeName } from "json-schema";
import type { OpenAPIV2, OpenAPIV3, OpenAPIV3_1 } from "openapi-types";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

interface liftSampleHelperConfig {
  includeReadOnly?: boolean;
  includeWriteOnly?: boolean;
}

type SwaggerJSONSchema = {
  [key: string]: {
    deprecated?: boolean;
    readOnly?: boolean;
    writeOnly?: boolean;
  };
} & JSONSchema7;

type OpenAPIJSONSchema =
  | OpenAPIV2.SchemaObject
  | Exclude<OpenAPIV3.SchemaObject, OpenAPIV3.NonArraySchemaObject>
  | Exclude<OpenAPIV3_1.SchemaObject, OpenAPIV3_1.NonArraySchemaObject>;

type OpenAPIJSONSchemaKeys = keyof OpenAPIJSONSchema;

const generateStringFromRegex = (pattern: string): string => {
  try {
    const randexp = new RandExp(pattern);
    return randexp.gen();
  } catch (e) {
    // Invalid regex should not cause a crash (regex syntax varies across languages)
    return "string";
  }
};

// Deeply strips a specific key from an object.
//
// `predicate` can be used to discriminate the stripping further,
// by preserving the key's place in the object based on its value.
const deeplyStripKey = (
  input: unknown,
  keyToStrip: string,
  predicate: (...args: unknown[]) => boolean = () => true
) => {
  if (
    typeof input !== "object" ||
    Array.isArray(input) ||
    input === null ||
    !keyToStrip
  ) {
    return input;
  }

  const obj: Record<string, unknown> = Object.assign({}, input) as Record<
    string,
    unknown
  >;

  Object.keys(obj).forEach((k) => {
    if (k === keyToStrip && predicate(obj[k], k)) {
      delete obj[k];
      return;
    }
    obj[k] = deeplyStripKey(obj[k], keyToStrip, predicate);
  });

  return obj;
};

const primitives: {
  [key: `${JSONSchema7TypeName}${string}`]: (
    schema: JSONSchema7
  ) => string | number | boolean;
} = {
  string: (schema: JSONSchema7) =>
    schema.pattern ? generateStringFromRegex(schema.pattern) : "string",
  string_email: () => "user@example.com",
  "string_date-time": () => new Date().toISOString(),
  string_date: () => new Date().toISOString().substring(0, 10),
  string_uuid: () => "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  string_hostname: () => "example.com",
  string_ipv4: () => "198.51.100.42",
  string_ipv6: () => "2001:0db8:5b96:0000:0000:426f:8e17:642a",
  number: () => 0,
  number_float: () => 0.0,
  integer: () => 0,
  boolean: (schema: JSONSchema7) =>
    typeof schema.default === "boolean" ? schema.default : true,
};

const primitive = (schema: JSONSchema7) => {
  schema = schema as JSONSchema7;
  const { type, format } = schema;

  if (typeof type !== "string") {
    return "Unknown Type: " + schema.type;
  }

  const fn = primitives[`${type}_${format}`] || primitives[type];
  if (typeof fn === "function") {
    return fn(schema);
  }
  return "Unknown Type: " + schema.type;
};

// do a couple of quick sanity tests to ensure the value
// looks like a $$ref that swagger-client generates.
const sanitizeRef = (value: Record<string, unknown>) =>
  deeplyStripKey(
    value,
    "$$ref",
    (val: unknown) => typeof val === "string" && val.indexOf("#") > -1
  );

const objectContracts: OpenAPIJSONSchemaKeys[] = [
  "maxProperties",
  "minProperties",
];
const arrayContracts: OpenAPIJSONSchemaKeys[] = ["minItems", "maxItems"];
const numberContracts: OpenAPIJSONSchemaKeys[] = [
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
];
const stringContracts: OpenAPIJSONSchemaKeys[] = ["minLength", "maxLength"];

const isEmpty = (value: SafeAny) => {
  if (value == null) {
    return true;
  }
  if (Array.isArray(value) || typeof value === "string") {
    return !value.length;
  }
  if (typeof value === "object") {
    return !Object.keys(value).length;
  }
  return false;
};

const normalizeArray = <T = unknown>(arr: T | T[]): T[] | [T] => {
  if (Array.isArray(arr)) return arr;
  return [arr];
};

const liftSampleHelper = (
  oldSchema: OpenAPIJSONSchema,
  target: OpenAPIJSONSchema,
  config: liftSampleHelperConfig = {}
) => {
  const setIfNotDefinedInTarget = (key: keyof OpenAPIJSONSchema) => {
    if (target[key] === undefined && oldSchema[key] !== undefined) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      target[key] = oldSchema[key];
    }
  };

  (
    [
      "example",
      "default",
      "enum",
      "xml",
      "type",
      ...objectContracts,
      ...arrayContracts,
      ...numberContracts,
      ...stringContracts,
    ] as Array<keyof OpenAPIJSONSchema>
  ).forEach((key) => setIfNotDefinedInTarget(key));

  if (oldSchema.required !== undefined && Array.isArray(oldSchema.required)) {
    if (target.required === undefined || !target.required.length) {
      target.required = [];
    }
    oldSchema.required.forEach((key) => {
      if (target.required!.includes(key)) {
        return;
      }
      target.required!.push(key);
    });
  }
  if (oldSchema.properties) {
    if (!target.properties) {
      target.properties = {};
    }
    const props = oldSchema.properties as SwaggerJSONSchema;
    for (const propName in props) {
      if (!Object.prototype.hasOwnProperty.call(props, propName)) {
        continue;
      }
      if (props[propName] && props[propName].deprecated) {
        continue;
      }
      if (
        props[propName] &&
        props[propName].readOnly &&
        !config.includeReadOnly
      ) {
        continue;
      }
      if (
        props[propName] &&
        props[propName].writeOnly &&
        !config.includeWriteOnly
      ) {
        continue;
      }
      if (!target.properties[propName]) {
        target.properties[propName] = props[propName];
        if (
          !oldSchema.required ||
          (Array.isArray(oldSchema.required) &&
            oldSchema.required.indexOf(propName) !== -1)
        ) {
          if (!target.required) {
            target.required = [propName];
          } else {
            target.required.push(propName);
          }
        }
      }
    }
  }

  if (oldSchema.items) {
    if (!target.items) {
      target.items = {};
    }
    target.items = liftSampleHelper(
      oldSchema.items as OpenAPIJSONSchema,
      target.items as OpenAPIJSONSchema,
      config
    ) as OpenAPIJSONSchema["items"];
  }

  return target;
};

export interface SampleFromSchemaConfig {
  includeReadOnly?: boolean;
  includeWriteOnly?: boolean;
}

export const sampleFromSchemaGeneric = (
  schema: OpenAPIJSONSchema,
  config: SampleFromSchemaConfig = {},
  exampleOverride: SafeAny = undefined,
  respectXML = false
): SafeAny => {
  let usePlainValue =
    exampleOverride !== undefined ||
    (schema && schema.example !== undefined) ||
    (schema && schema.default !== undefined);
  // first check if there is the need of combining this schema with others required by allOf
  const hasOneOf =
    !usePlainValue && schema && schema.oneOf && schema.oneOf.length > 0;
  const hasAnyOf =
    !usePlainValue && schema && schema.anyOf && schema.anyOf.length > 0;
  if (!usePlainValue && (hasOneOf || hasAnyOf)) {
    const schemaToAdd = (
      hasOneOf ? schema.oneOf![0] : schema.anyOf![0]
    ) as OpenAPIJSONSchema;
    liftSampleHelper(schemaToAdd, schema, config);
    if (!schema.xml && schemaToAdd.xml) {
      schema.xml = schemaToAdd.xml;
    }
    if (schema.example !== undefined && schemaToAdd.example !== undefined) {
      usePlainValue = true;
    } else if (schemaToAdd.properties) {
      if (!schema.properties) {
        schema.properties = {};
      }
      const props = schemaToAdd.properties as SwaggerJSONSchema;
      for (const propName in props) {
        if (!Object.prototype.hasOwnProperty.call(props, propName)) {
          continue;
        }
        if (props[propName] && props[propName].deprecated) {
          continue;
        }
        if (
          props[propName] &&
          props[propName].readOnly &&
          !config.includeReadOnly
        ) {
          continue;
        }
        if (
          props[propName] &&
          props[propName].writeOnly &&
          !config.includeWriteOnly
        ) {
          continue;
        }
        if (!schema.properties[propName]) {
          schema.properties[propName] = props[propName];
          if (
            !schemaToAdd.required ||
            (Array.isArray(schemaToAdd.required) &&
              schemaToAdd.required.indexOf(propName) !== -1)
          ) {
            if (!schema.required) {
              schema.required = [propName];
            } else {
              schema.required.push(propName);
            }
          }
        }
      }
    }
  }
  const _attr: { [key: string]: string } = {};
  const { example, properties, additionalProperties } = schema || {};
  const items =
    (schema.items as OpenAPIV3.SchemaObject | OpenAPIV3_1.SchemaObject) ||
    undefined;
  let { xml, type } = schema || {};
  const { includeReadOnly, includeWriteOnly } = config;
  xml = xml || {};
  let { name } = xml;
  const { prefix, namespace } = xml;
  let displayName: string;
  let res: SafeAny = {};

  // set xml naming and attributes
  if (respectXML) {
    name = name || "notagname";
    // add prefix to name if exists
    displayName = (prefix ? prefix + ":" : "") + name;
    if (namespace) {
      //add prefix to namespace if exists
      const namespacePrefix = prefix ? "xmlns:" + prefix : "xmlns";
      _attr[namespacePrefix] = namespace;
    }
    // init xml default response sample obj
    res[displayName] = [];
  }

  const schemaHasAny = (keys: Array<keyof OpenAPIJSONSchema>) =>
    keys.some((key) => Object.prototype.hasOwnProperty.call(schema, key));
  // try recover missing type
  if (schema && !type) {
    if (properties || additionalProperties || schemaHasAny(objectContracts)) {
      type = "object";
    } else if (items || schemaHasAny(arrayContracts)) {
      type = "array";
    } else if (schemaHasAny(numberContracts)) {
      type = "number";
      schema.type = "number";
    } else if (!usePlainValue && !schema.enum) {
      // implicit cover schemaHasAny(stringContracts) or A schema without a type matches any data type is:
      // components:
      //   schemas:
      //     AnyValue:
      //       anyOf:
      //         - type: string
      //         - type: number
      //         - type: integer
      //         - type: boolean
      //         - type: array
      //           items: {}
      //         - type: object
      //
      // which would resolve to type: string
      type = "string";
      schema.type = "string";
    }
  }

  const handleMinMaxItems = (sampleArray: Record<string, unknown>[]) => {
    if (schema?.maxItems !== null && schema?.maxItems !== undefined) {
      sampleArray = sampleArray.slice(0, schema?.maxItems);
    }
    if (schema?.minItems !== null && schema?.minItems !== undefined) {
      let i = 0;
      while (sampleArray.length < schema?.minItems) {
        sampleArray.push(sampleArray[i++ % sampleArray.length]);
      }
    }
    return sampleArray;
  };

  // add to result helper init for xml or json
  const props = properties! as { [p: string]: OpenAPIJSONSchema };
  let addPropertyToResult;
  let propertyAddedCounter = 0;

  const hasExceededMaxProperties = () =>
    schema &&
    schema.maxProperties !== null &&
    schema.maxProperties !== undefined &&
    propertyAddedCounter >= schema.maxProperties;

  const requiredPropertiesToAdd = () => {
    if (!schema || !schema.required) {
      return 0;
    }
    let addedCount = 0;
    if (respectXML) {
      schema.required.forEach(
        (key) => (addedCount += res[key] === undefined ? 0 : 1)
      );
    } else {
      schema.required.forEach(
        (key) =>
          (addedCount +=
            res[displayName]?.find((x: SafeAny) => x[key] !== undefined) ===
            undefined
              ? 0
              : 1)
      );
    }
    return schema.required.length - addedCount;
  };

  const isOptionalProperty = (propName: string) => {
    if (!schema || !schema.required || !schema.required.length) {
      return true;
    }
    return !schema.required.includes(propName);
  };

  const canAddProperty = (propName: string) => {
    if (
      !schema ||
      schema.maxProperties === null ||
      schema.maxProperties === undefined
    ) {
      return true;
    }
    if (hasExceededMaxProperties()) {
      return false;
    }
    if (!isOptionalProperty(propName)) {
      return true;
    }
    return (
      schema.maxProperties - propertyAddedCounter - requiredPropertiesToAdd() >
      0
    );
  };

  if (respectXML) {
    addPropertyToResult = (propName: string, overrideE = undefined) => {
      if (schema && props[propName]) {
        // case it is an xml attribute
        props[propName].xml = props[propName].xml || {};

        if (props[propName].xml!.attribute) {
          const enumAttrVal = Array.isArray(props[propName].enum)
            ? props[propName].enum![0]
            : undefined;
          const attrExample = props[propName].example;
          const attrDefault = props[propName].default;

          if (attrExample !== undefined) {
            _attr[props[propName].xml!.name || propName] = attrExample;
          } else if (attrDefault !== undefined) {
            _attr[props[propName].xml!.name || propName] = attrDefault;
          } else if (enumAttrVal !== undefined) {
            _attr[props[propName].xml!.name || propName] = enumAttrVal;
          } else {
            _attr[props[propName].xml!.name || propName] = primitive(
              props[propName] as JSONSchema7
            ) as string;
          }

          return;
        }
        props[propName].xml!.name = props[propName].xml!.name || propName;
      } else if (!props[propName] && additionalProperties !== false) {
        // case only additionalProperty that is not defined in schema
        props[propName] = {
          xml: {
            name: propName,
          },
        };
      }

      const t = sampleFromSchemaGeneric(
        (schema && props[propName]) || undefined,
        config,
        overrideE,
        respectXML
      );
      if (!canAddProperty(propName)) {
        return;
      }

      propertyAddedCounter++;
      if (Array.isArray(t)) {
        res[displayName] = res[displayName].concat(t);
      } else {
        res[displayName].push(t);
      }
    };
  } else {
    addPropertyToResult = (propName: string, overrideE: SafeAny) => {
      if (!canAddProperty(propName)) {
        return;
      }
      if (
        Object.prototype.hasOwnProperty.call(schema, "discriminator") &&
        schema.discriminator &&
        Object.prototype.hasOwnProperty.call(schema.discriminator, "mapping") &&
        (schema.discriminator as OpenAPIV3.DiscriminatorObject).mapping &&
        Object.prototype.hasOwnProperty.call(schema, "$$ref") &&
        // TODO this is a hack, the $$ref should be a string
        (schema as SafeAny).$$ref &&
        (schema.discriminator as OpenAPIV3.DiscriminatorObject).propertyName ===
          propName
      ) {
        for (const pair in (
          schema.discriminator as OpenAPIV3.DiscriminatorObject
        ).mapping) {
          if (
            (schema as SafeAny).$$ref.search(
              (schema.discriminator as OpenAPIV3.DiscriminatorObject).mapping![
                pair
              ]
            ) !== -1
          ) {
            res[propName] = pair;
            break;
          }
        }
      } else {
        res[propName] = sampleFromSchemaGeneric(
          props[propName],
          config,
          overrideE,
          respectXML
        );
      }
      propertyAddedCounter++;
    };
  }

  // check for plain value and if found use it to generate sample from it
  if (usePlainValue) {
    let sample: SafeAny;
    if (exampleOverride !== undefined) {
      sample = sanitizeRef(exampleOverride);
    } else if (example !== undefined) {
      sample = sanitizeRef(example);
    } else {
      sample = sanitizeRef(schema.default);
    }

    // if json just return
    if (!respectXML) {
      // spacial case yaml parser can not know about
      if (typeof sample === "number" && type === "string") {
        return `${sample}`;
      }
      // return if sample does not need any parsing
      if (typeof sample !== "string" || type === "string") {
        return sample;
      }
      // check if sample is parsable or just a plain string
      try {
        return JSON.parse(sample);
      } catch (e) {
        // sample is just plain string return it
        return sample;
      }
    }

    // recover missing type
    if (!schema) {
      type = Array.isArray(sample) ? "array" : typeof sample;
    }

    // generate xml sample recursively for array case
    if (type === "array") {
      if (!Array.isArray(sample)) {
        if (typeof sample === "string") {
          return sample;
        }
        sample = [sample];
      }
      const itemSchema = schema
        ? (schema.items as OpenAPIV3.SchemaObject | OpenAPIV3_1.SchemaObject)
        : undefined;
      if (itemSchema) {
        itemSchema.xml = itemSchema.xml || xml || {};
        itemSchema.xml.name = itemSchema.xml.name || xml.name;
      }
      let itemSamples = sample.map((s: string) =>
        sampleFromSchemaGeneric(
          itemSchema as OpenAPIJSONSchema,
          config,
          s,
          respectXML
        )
      );
      itemSamples = handleMinMaxItems(itemSamples);
      if (xml.wrapped) {
        res[displayName!] = itemSamples;
        if (!isEmpty(_attr)) {
          res[displayName!].push({ _attr: _attr });
        }
      } else {
        res = itemSamples;
      }
      return res;
    }

    // generate xml sample recursively for object case
    if (type === "object") {
      // case literal example
      if (typeof sample === "string") {
        return sample;
      }
      for (const propName in sample) {
        if (!Object.prototype.hasOwnProperty.call(sample, propName)) {
          continue;
        }
        if (
          schema &&
          props[propName] &&
          props[propName].readOnly &&
          !includeReadOnly
        ) {
          continue;
        }
        if (
          schema &&
          props[propName] &&
          props[propName].writeOnly &&
          !includeWriteOnly
        ) {
          continue;
        }
        if (
          schema &&
          props[propName] &&
          props[propName].xml &&
          props[propName].xml!.attribute
        ) {
          _attr[props[propName].xml!.name || propName] = sample[propName];
          continue;
        }
        addPropertyToResult(propName, sample[propName]);
      }
      if (!isEmpty(_attr)) {
        res[displayName!].push({ _attr: _attr });
      }

      return res;
    }

    res[displayName!] = !isEmpty(_attr) ? [{ _attr: _attr }, sample] : sample;
    return res;
  }

  // use schema to generate sample

  if (type === "object") {
    for (const propName in props) {
      if (!Object.prototype.hasOwnProperty.call(props, propName)) {
        continue;
      }
      if (props[propName] && props[propName].deprecated) {
        continue;
      }
      if (props[propName] && props[propName].readOnly && !includeReadOnly) {
        continue;
      }
      if (props[propName] && props[propName].writeOnly && !includeWriteOnly) {
        continue;
      }
      addPropertyToResult(propName);
    }
    if (respectXML && _attr) {
      res[displayName!].push({ _attr: _attr });
    }

    if (hasExceededMaxProperties()) {
      return res;
    }

    if (additionalProperties === true) {
      if (respectXML) {
        res[displayName!].push({ additionalProp: "Anything can be here" });
      } else {
        res.additionalProp1 = {};
      }
      propertyAddedCounter++;
    } else if (additionalProperties) {
      const additionalProps = additionalProperties as
        | OpenAPIV3.SchemaObject
        | OpenAPIV3_1.SchemaObject;
      const additionalPropSample = sampleFromSchemaGeneric(
        additionalProps as OpenAPIJSONSchema,
        config,
        undefined,
        respectXML
      );

      if (
        respectXML &&
        additionalProps.xml &&
        additionalProps.xml.name &&
        additionalProps.xml.name !== "notagname"
      ) {
        res[displayName!].push(additionalPropSample);
      } else {
        const toGenerateCount =
          schema.minProperties !== null &&
          schema.minProperties !== undefined &&
          propertyAddedCounter < schema.minProperties
            ? schema.minProperties - propertyAddedCounter
            : 3;
        for (let i = 1; i <= toGenerateCount; i++) {
          if (hasExceededMaxProperties()) {
            return res;
          }
          if (respectXML) {
            const temp: Record<string, SafeAny> = {};
            temp["additionalProp" + i] = additionalPropSample["notagname"];
            res[displayName!].push(temp);
          } else {
            res["additionalProp" + i] = additionalPropSample;
          }
          propertyAddedCounter++;
        }
      }
    }
    return res;
  }

  if (type === "array") {
    if (!items) {
      return;
    }

    let sampleArray;
    if (respectXML) {
      items.xml = items.xml || schema?.xml || {};
      items.xml.name = items.xml.name || xml.name;
    }

    if (Array.isArray(items.anyOf)) {
      sampleArray = items.anyOf.map((i) =>
        sampleFromSchemaGeneric(
          liftSampleHelper(
            items as OpenAPIJSONSchema,
            i as OpenAPIJSONSchema,
            config
          ),
          config,
          undefined,
          respectXML
        )
      );
    } else if (Array.isArray(items.oneOf)) {
      sampleArray = items.oneOf.map((i) =>
        sampleFromSchemaGeneric(
          liftSampleHelper(
            items as OpenAPIJSONSchema,
            i as OpenAPIJSONSchema,
            config
          ),
          config,
          undefined,
          respectXML
        )
      );
    } else if (!respectXML || (respectXML && xml.wrapped)) {
      sampleArray = [
        sampleFromSchemaGeneric(
          items as OpenAPIJSONSchema,
          config,
          undefined,
          respectXML
        ),
      ];
    } else {
      return sampleFromSchemaGeneric(
        items as OpenAPIJSONSchema,
        config,
        undefined,
        respectXML
      );
    }
    sampleArray = handleMinMaxItems(sampleArray);
    if (respectXML && xml.wrapped) {
      res[displayName!] = sampleArray;
      if (!isEmpty(_attr)) {
        res[displayName!].push({ _attr: _attr });
      }
      return res;
    }
    return sampleArray;
  }

  let value;
  if (schema && Array.isArray(schema.enum)) {
    //display enum first value
    value = normalizeArray(schema.enum)[0];
  } else if (schema) {
    // display schema default
    value = primitive(schema as JSONSchema7);
    if (typeof value === "number") {
      let min = schema.minimum;
      if (min !== undefined && min !== null) {
        if (schema.exclusiveMinimum) {
          min++;
        }
        value = min;
      }
      let max = schema.maximum;
      if (max !== undefined && max !== null) {
        if (schema.exclusiveMaximum) {
          max--;
        }
        value = max;
      }
    }
    if (typeof value === "string") {
      if (schema.maxLength !== null && schema.maxLength !== undefined) {
        value = value.slice(0, schema.maxLength);
      }
      if (schema.minLength !== null && schema.minLength !== undefined) {
        let i = 0;
        while (value.length < schema.minLength) {
          value += value[i++ % value.length];
        }
      }
    }
  } else {
    return;
  }
  if (type === "file") {
    return;
  }

  if (respectXML) {
    res[displayName!] = !isEmpty(_attr) ? [{ _attr: _attr }, value] : value;
    return res;
  }

  return value;
};

export const sampleFromSchema = (
  schema: OpenAPIJSONSchema,
  config: SampleFromSchemaConfig,
  o: SafeAny = undefined
) => sampleFromSchemaGeneric(schema, config, o, false);
