import { memo, useState } from "react";
import { JSONSchema7, JSONSchema7Definition } from "json-schema";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { css } from "@emotion/react";
import { css as classNameCss } from "@emotion/css";
import validator from "@rjsf/validator-ajv8";
import { Button, Checkbox, Col, Row } from "antd";
import { Form } from "@rjsf/antd";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  LeptonAPIItem,
  SchemaObject,
} from "@lepton-dashboard/services/open-api.service";
const convertToOptionalSchema = (schema: SchemaObject): JSONSchema7 => {
  const optionalSchema: JSONSchema7 = {
    properties: {},
    type: "object",
  };
  const { properties, required } = schema;
  const requiredProperties: JSONSchema7["properties"] = {};
  if (properties && required) {
    Object.keys(properties).forEach((key) => {
      const propertyValue = properties[key] as JSONSchema7Definition;
      if (required.indexOf(key) === -1) {
        optionalSchema.properties![key] = propertyValue;
      } else {
        requiredProperties[key] = propertyValue;
      }
    });
  }
  return {
    properties: {
      ...requiredProperties,
      optional: optionalSchema,
    },
    type: schema.type,
    required: schema.required,
  };
};

interface SchemaDataWithOptional {
  [k: string]: unknown;
  optional?: Record<string, unknown>;
}
const convertToOptionalSchemaData = (
  schema: SchemaObject,
  initData: Record<string, unknown>
): SchemaDataWithOptional => {
  const { required } = schema;
  const data: SchemaDataWithOptional = {};
  if (initData && required) {
    Object.keys(initData).forEach((key) => {
      const dataValue = initData[key];
      if (required.indexOf(key) !== -1) {
        data[key] = dataValue;
      } else {
        if (data.optional) {
          data.optional[key] = dataValue;
        } else {
          data.optional = {};
        }
      }
    });
  }
  return data;
};

const isSchemaDataWithOptional = (
  data: unknown
): data is SchemaDataWithOptional => {
  return typeof data === "object" && data !== null && "optional" in data;
};

const convertToSchemaFormData = (
  data: Record<string, unknown> | SchemaDataWithOptional
): Record<string, unknown> => {
  if (isSchemaDataWithOptional(data)) {
    const convertedData = { ...data, ...data.optional };
    delete convertedData.optional;
    return convertedData;
  } else {
    return data;
  }
};

export const SchemaForm = memo<{
  api: LeptonAPIItem;
  deployment: Deployment;
  resultChange: (value: unknown) => void;
}>(
  ({ deployment, resultChange, api }) => {
    const theme = useAntdTheme();
    const convertedSchema = convertToOptionalSchema(api.schema!);
    const convertedInitData = convertToOptionalSchemaData(
      api.schema!,
      (api.request ? api.request.body : {}) as Record<string, unknown>
    );
    const deploymentService = useInject(DeploymentService);
    const hasAdvanced =
      Object.keys(
        (convertedSchema.properties!.optional as JSONSchema7)!.properties!
      ).length > 0;
    const request = (value: unknown) => {
      setLoading(true);
      const request = {
        ...api.request!,
        body: value,
      } as LeptonAPIItem["request"];
      deploymentService.request(deployment.name, request!).subscribe({
        next: (data) => {
          resultChange(data);
          setLoading(false);
        },
        error: () => setLoading(false),
      });
    };
    const [loading, setLoading] = useState(false);
    const [advanced, setAdvanced] = useState(false);
    const [data, setData] = useState(convertedInitData);
    return (
      <Form
        focusOnFirstError
        validator={validator}
        schema={convertedSchema}
        formData={data}
        uiSchema={{
          optional: {
            "ui:title": "",
            "ui:classNames": advanced
              ? classNameCss`display:block`
              : classNameCss`display:none;`,
          },
        }}
        onChange={({ formData }) => {
          setData(formData);
        }}
        onSubmit={({ formData }) => {
          setData(formData);
          const schemaFormData = convertToSchemaFormData(formData);
          request(schemaFormData);
        }}
        css={css`
          fieldset {
            all: unset;
            display: block;
            fieldset {
              margin: 8px 0;
              border-radius: ${theme.borderRadius}px;
              padding: 16px 24px;
              border: 1px solid ${theme.colorBorder};
              background: ${theme.colorBgLayout};
            }
          }
          .ant-form-item {
            margin-bottom: 4px !important;
          }
          .ant-form-item-label {
            padding: 0 !important;
          }
          #root_optional {
            border: 1px solid ${theme.colorBorder};
            background: ${theme.colorBgLayout};
            border-radius: ${theme.borderRadius}px;
            margin: 16px 0 8px 0;
            padding: 16px;
          }
        `}
      >
        <Row
          css={css`
            margin-top: 16px;
          `}
        >
          <Col flex="1 1 auto">
            <Button loading={loading} type="primary" htmlType="submit">
              Submit
            </Button>
          </Col>
          <Col
            flex="0 0 auto"
            css={css`
              display: flex;
              align-items: center;
            `}
          >
            {hasAdvanced && (
              <Checkbox
                checked={advanced}
                onChange={(v) => setAdvanced(v.target.checked)}
              >
                Show advanced options
              </Checkbox>
            )}
          </Col>
        </Row>
      </Form>
    );
  },
  (prevProps, nextProps) =>
    prevProps.api.operationId === nextProps.api.operationId
);
