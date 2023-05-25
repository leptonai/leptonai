import { FC, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { useOutletContext } from "react-router-dom";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { JsonSchemaService } from "@lepton-dashboard/services/json-schema.service";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { Alert, Col, Row, Select, Typography } from "antd";
import { Result } from "@lepton-dashboard/routers/deployments/routers/detail/routers/demo/components/result";
import { css } from "@emotion/react";
import { SchemaForm } from "@lepton-dashboard/routers/deployments/routers/detail/routers/demo/components/schema-form";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const Demo: FC = () => {
  const theme = useAntdTheme();
  const [loading, setLoading] = useState(true);
  const deployment = useOutletContext<Deployment>();
  const photonService = useInject(PhotonService);
  const [path, setPath] = useState<string | undefined>(undefined);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined,
    {
      next: (p) => {
        if (!path) {
          const paths = jsonSchemaService.getPaths(p?.openapi_schema);
          setPath(paths[0]);
        }
        setLoading(false);
      },
      error: () => setLoading(false),
    }
  );
  const jsonSchemaService = useInject(JsonSchemaService);
  const [result, setResult] = useState<SafeAny>("output should appear here");
  const paths = jsonSchemaService.getPaths(photon?.openapi_schema);
  const { inputSchema, inputExample } = useMemo(() => {
    return jsonSchemaService.parse(photon?.openapi_schema, path);
  }, [jsonSchemaService, path, photon?.openapi_schema]);
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
        {inputSchema && path && paths.length > 0 ? (
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
                    onChange={(v) => setPath(v)}
                    options={paths.map((i) => {
                      return { label: i, value: i };
                    })}
                  />
                </Col>
              </Row>
              <SchemaForm
                path={path}
                deployment={deployment}
                initData={inputExample}
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
