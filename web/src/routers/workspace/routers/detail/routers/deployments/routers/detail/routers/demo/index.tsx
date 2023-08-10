import { FC, useEffect, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Select, Spin, Typography } from "antd";
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
import { OpenAPI } from "openapi-types";
import { MethodTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo/components/method-tag";
import { LoadingOutlined } from "@ant-design/icons";

export const Demo: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();

  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);

  const [initialized, setInitialized] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apis, setApis] = useState<LeptonAPIItem[]>([]);
  const [resolvedSchema, setResolvedSchema] = useState<OpenAPI.Document | null>(
    null
  );
  const photons = useStateFromBehaviorSubject(photonService.list());
  const photon = useMemo(() => {
    return photons.find((p) => p.id === deployment.photon_id);
  }, [deployment.photon_id, photons]);

  const [operationId, setOperationId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const parseSchema = async () => {
      if (photon?.openapi_schema) {
        const url = deployment.status.endpoint.external_endpoint;
        const res = await openApiService.parse({
          ...photon.openapi_schema,
          servers:
            photon.openapi_schema?.servers?.length > 0
              ? photon.openapi_schema.servers
              : [{ url }],
        });
        setResolvedSchema(res);
        const apis = res ? openApiService.convertToLeptonAPIItems(res) : [];

        setApis(apis);
        if (apis.length) {
          if (!operationId) {
            setOperationId(apis[0].operationId);
          }
        } else {
          setOperationId(undefined);
        }
      }
      setInitialized(true);
    };
    parseSchema().then();
  }, [deployment, operationId, openApiService, photon, setApis]);

  const [result, setResult] = useState<DEMOResult>({
    payload: "output should appear here",
    contentType: "text/plain",
  });

  const currentAPI = useMemo(() => {
    return apis.find((i) => i.operationId === operationId);
  }, [apis, operationId]);

  return initialized ? (
    <Card
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
            <Col span={24} md={12}>
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
                  onLoadingChange={setSubmitting}
                  api={currentAPI!}
                />
              ) : null}
            </Col>
            <Col span={24} md={12}>
              <Spin
                spinning={submitting}
                indicator={
                  <LoadingOutlined
                    css={css`
                      font-size: 36px !important;
                      margin: -18px !important;
                    `}
                    spin
                  />
                }
                delay={500}
              >
                <Result result={result} />
              </Spin>
            </Col>
          </Row>
        ) : (
          <Alert showIcon type="warning" message="No openapi schema found" />
        )}
      </Alert.ErrorBoundary>
    </Card>
  ) : null;
};
