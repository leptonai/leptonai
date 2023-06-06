import { FC, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { Alert, Col, Row, Select, Typography } from "antd";
import { Result } from "@lepton-dashboard/routers/deployments/routers/detail/routers/demo/components/result";
import { css } from "@emotion/react";
import { SchemaForm } from "@lepton-dashboard/routers/deployments/routers/detail/routers/demo/components/schema-form";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  OpenApiService,
  OperationWithPath,
  SchemaObject,
} from "@lepton-dashboard/services/open-api.service";
import { from, switchMap } from "rxjs";

export const Demo: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();

  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);

  const [loading, setLoading] = useState(true);
  const [operations, setOperations] = useState<OperationWithPath[]>([]);
  const [operationId, setOperationId] = useState<string | undefined>(undefined);
  useStateFromObservable(
    () =>
      photonService.id(deployment.photon_id).pipe(
        switchMap((p) => {
          if (p?.openapi_schema) {
            return from(openApiService.parse(p.openapi_schema));
          }
          return from(Promise.resolve(null));
        })
      ),
    undefined,
    {
      next: (schema) => {
        if (schema) {
          const operations = openApiService.listOperations(schema);
          setOperations(operations);

          if (!operationId) {
            if (operations.length > 0) {
              setOperationId(operations[0].operationId);
            }
          }
        } else {
          setOperationId(undefined);
        }

        setLoading(false);
      },
      error: () => setLoading(false),
    }
  );

  const [result, setResult] = useState<SafeAny>("output should appear here");
  const { inputSchema, requestBody } = useMemo(() => {
    const operation = operations.find((i) => i.operationId === operationId);
    if (operation) {
      const contents = openApiService.listMediaTypeObjects(operation);
      let requestBody: SafeAny = null;
      if (contents["application/json"]) {
        requestBody = openApiService.sampleFromSchema(
          contents["application/json"].schema,
          contents["application/json"].example
        );
      }
      return {
        inputSchema: contents["application/json"]?.schema as SchemaObject,
        requestBody,
      };
    } else {
      return { inputSchema: {}, requestBody: {} };
    }
  }, [operations, operationId, openApiService]);

  const path = useMemo(() => {
    const operation = operations.find((i) => i.operationId === operationId);
    return operation?.path ?? "";
  }, [operations, operationId]);

  return (
    <Card
      loading={loading}
      shadowless
      borderless
      css={css`
        .ant-alert-description pre {
          font-family: ${theme.fontFamily};
        }
      `}
    >
      <Alert.ErrorBoundary
        message={null}
        description="Parsing schema failed, please try call API manually."
      >
        {operationId}
        {operations.length}
        {inputSchema && operationId && operations.length > 0 ? (
          <Row gutter={[32, 16]}>
            <Col flex="1 0 400px">
              <Row
                css={css`
                  margin-bottom: 12px;
                `}
              >
                <Col
                  css={css`
                    display: flex;
                    align-items: center;
                  `}
                  flex="0 0 40px"
                >
                  <Typography.Text>Path:</Typography.Text>
                </Col>
                <Col flex="auto">
                  <Select
                    css={css`
                      width: 100%;
                    `}
                    value={path}
                    onChange={(v) => setOperationId(v)}
                    options={operations.map((i) => {
                      return { label: i.path, value: i.operationId };
                    })}
                  />
                </Col>
              </Row>
              <SchemaForm
                path={path}
                deployment={deployment}
                initData={requestBody}
                resultChange={setResult}
                schema={inputSchema}
              />
            </Col>
            <Col flex="1 1 400px">
              <Result result={result} />
            </Col>
          </Row>
        ) : (
          <Alert showIcon type="warning" message="No openapi schema found" />
        )}
      </Alert.ErrorBoundary>
    </Card>
  );
};
