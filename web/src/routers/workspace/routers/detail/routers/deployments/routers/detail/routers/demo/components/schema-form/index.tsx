import { memo, useState } from "react";
import { JSONSchema7, JSONSchema7Definition } from "json-schema";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { css } from "@emotion/react";
import { css as classNameCss } from "@emotion/css";
import validator from "@rjsf/validator-ajv8";
import { Button, Checkbox, Col, Row } from "antd";
import { Form } from "@lepton-libs/rjsf";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  LeptonAPIItem,
  SchemaObject,
} from "@lepton-dashboard/services/open-api.service";
import { englishStringTranslator } from "@rjsf/utils";
import {
  DEMOResult,
  SupportedContentTypes,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo/components/result";
import { from, map, mergeMap } from "rxjs";
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
  resultChange: (value: DEMOResult) => void;
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
      deploymentService
        .request(deployment.name, request!)
        .pipe(
          mergeMap((res) => {
            const contentType: SupportedContentTypes =
              (res.headers.get("content-type") as SupportedContentTypes) ||
              "text/plain";
            if (contentType.indexOf("application/json") !== -1) {
              return from(res.json()).pipe(
                map((data) => ({ data, contentType }))
              );
            } else if (contentType.indexOf("text/plain") !== -1) {
              return from(res.text()).pipe(
                map((data) => ({ data, contentType }))
              );
            } else {
              return from(res.blob()).pipe(
                map((data) => ({ data, contentType }))
              );
            }
          })
        )
        .subscribe({
          next: (res) => {
            resultChange({
              payload: res.data,
              contentType: res.contentType,
            });
            setLoading(false);
          },
          error: (err: Response | Error) => {
            if (err instanceof Response) {
              const errors: string[] = [];
              errors.push(`Request failed with status code ${err.status}`);
              const contentType = err.headers.get("content-type");
              let errorPromise: Promise<string>;
              if (
                contentType &&
                contentType.indexOf("application/json") !== -1
              ) {
                errorPromise = err
                  .json()
                  .then((data) => JSON.stringify(data, null, 2));
              } else {
                errorPromise = err.text();
              }
              errorPromise.then((data) => {
                errors.push(data);
                resultChange({
                  error: errors.join("\n"),
                });
                setLoading(false);
              });
            } else {
              resultChange({
                error: err.message,
              });
              setLoading(false);
            }
          },
        });
    };
    const [loading, setLoading] = useState(false);
    const [advanced, setAdvanced] = useState(false);
    const [data, setData] = useState(convertedInitData);
    return (
      <Form
        showErrorList={false}
        idPrefix="api-form"
        focusOnFirstError
        validator={validator}
        schema={convertedSchema}
        formData={data}
        translateString={(k, params) => {
          if (k === "%1 option %2") {
            return `Option${params ? ` ${params[1]}` : ""}`;
          }
          return englishStringTranslator(k, params);
        }}
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
