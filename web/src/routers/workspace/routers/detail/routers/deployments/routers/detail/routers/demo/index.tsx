import { FC, useMemo, useState } from "react";
import { Card } from "../../../../../../../../../../components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Select, Typography } from "antd";
import {
  DEMOResult,
  Result,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo/components/result";
import { css } from "@emotion/react";
import { SchemaForm } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo/components/schema-form";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";
import { OpenAPI } from "openapi-types";
import { MethodTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo/components/method-tag";

export const Demo: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();

  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);

  const [loading, setLoading] = useState(true);
  const [apis, setApis] = useState<LeptonAPIItem[]>([]);
  const [resolvedSchema, setResolvedSchema] = useState<OpenAPI.Document | null>(
    null
  );
  const [operationId, setOperationId] = useState<string | undefined>(undefined);
  useStateFromObservable(
    () =>
      photonService.id(deployment.photon_id).pipe(
        switchMap((p) => {
          if (p?.openapi_schema) {
            const url = deployment.status.endpoint.external_endpoint;
            return from(
              openApiService
                .parse({
                  ...p.openapi_schema,
                  servers:
                    p.openapi_schema?.servers?.length > 0
                      ? p.openapi_schema.servers
                      : [{ url }],
                })
                .then((res) => {
                  setResolvedSchema(res);
                  return res ? openApiService.convertToLeptonAPIItems(res) : [];
                })
            );
          }
          return of([]);
        })
      ),
    [],
    {
      next: (items) => {
        setApis(items);
        if (items.length) {
          if (!operationId) {
            setOperationId(items[0].operationId);
          }
        } else {
          setOperationId(undefined);
        }

        setLoading(false);
      },
      error: (err) => {
        console.error(err);
        setLoading(false);
      },
    }
  );

  const [result, setResult] = useState<DEMOResult>({
    payload: "output should appear here",
    contentType: "text/plain",
  });

  const currentAPI = useMemo(() => {
    return apis.find((i) => i.operationId === operationId);
  }, [apis, operationId]);

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
        {operationId && apis.length > 0 ? (
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
                  <Typography.Text>API:</Typography.Text>
                </Col>
                <Col flex="auto">
                  <Select
                    css={css`
                      width: 100%;
                    `}
                    value={currentAPI?.operationId}
                    onChange={(v) => setOperationId(v)}
                    options={apis.map((i) => {
                      return {
                        label: (
                          <Typography.Text
                            css={css`
                              display: inline-flex;
                              width: 100%;
                              justify-content: space-between;
                            `}
                          >
                            <Typography.Text>
                              {i.operation.path}
                            </Typography.Text>
                            {i.request?.method ? (
                              <MethodTag method={i.request.method} />
                            ) : null}
                          </Typography.Text>
                        ),
                        value: i.operationId,
                      };
                    })}
                  />
                </Col>
              </Row>
              {resolvedSchema && currentAPI ? (
                <SchemaForm
                  deployment={deployment}
                  resultChange={setResult}
                  api={currentAPI}
                />
              ) : null}
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
