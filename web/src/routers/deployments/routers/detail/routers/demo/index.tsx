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
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";

export const Demo: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();

  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);

  const [loading, setLoading] = useState(true);
  const [apis, setApis] = useState<LeptonAPIItem[]>([]);
  const [operationId, setOperationId] = useState<string | undefined>(undefined);
  useStateFromObservable(
    () =>
      photonService.id(deployment.photon_id).pipe(
        switchMap((p) => {
          if (p?.openapi_schema) {
            const url = deployment.status.endpoint.external_endpoint;
            return from(
              openApiService.convertToLeptonAPIItems({
                ...p.openapi_schema,
                servers:
                  p.openapi_schema?.servers?.length > 0
                    ? p.openapi_schema.servers
                    : [{ url }],
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

  const [result, setResult] = useState<SafeAny>("output should appear here");
  const { inputSchema, requestBody } = useMemo(() => {
    const api = apis.find((i) => i.operationId === operationId);
    if (api) {
      return {
        inputSchema: api.schema,
        requestBody: api.request ? api.request.body : {},
      };
    } else {
      return { inputSchema: {}, requestBody: {} };
    }
  }, [apis, operationId]);

  const currentPath = useMemo(() => {
    const api = apis.find((i) => i.operationId === operationId);
    return api?.operation?.path ?? "";
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
        {inputSchema && operationId && apis.length > 0 ? (
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
                    value={currentPath}
                    onChange={(v) => setOperationId(v)}
                    options={apis.map((i) => {
                      return { label: i.operation.path, value: i.operationId };
                    })}
                  />
                </Col>
              </Row>
              <SchemaForm
                path={currentPath}
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
