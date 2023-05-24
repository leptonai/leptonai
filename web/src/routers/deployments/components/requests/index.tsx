import { FC, useMemo, useState } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { Alert, Col, Row } from "antd";
import { SchemaForm } from "@lepton-dashboard/routers/deployments/components/schema-form";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { JsonSchemaService } from "@lepton-dashboard/services/json-schema.service";

export const Requests: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const jsonSchemaService = useInject(JsonSchemaService);
  const [result, setResult] = useState<SafeAny>("output should appear here");
  const { inputSchema, path, inputExample } = jsonSchemaService.parse(
    photon?.openapi_schema
  );
  const displayResult = useMemo(() => {
    if (typeof result === "string") {
      return result;
    } else if (typeof result === "object") {
      return JSON.stringify(result);
    } else {
      return "outputs format not supported";
    }
  }, [result]);
  return inputSchema && path ? (
    <Row gutter={[32, 16]}>
      <Col flex="1 0 400px">
        <SchemaForm
          path={path}
          deployment={deployment}
          initData={inputExample}
          resultChange={setResult}
          schema={inputSchema}
        />
      </Col>
      <Col flex="1 1 400px">
        <div
          css={css`
            margin: 0;
            background: ${theme.colorBgLayout};
            height: 100%;
            border: 1px solid ${theme.colorBorder};
            border-radius: ${theme.borderRadius}px;
            word-break: break-word;
            white-space: pre-wrap;
            color: ${theme.colorText};
            padding: 32px;
          `}
        >
          {displayResult}
        </div>
      </Col>
    </Row>
  ) : (
    <Alert showIcon type="warning" message="No openapi schema found" />
  );
};
