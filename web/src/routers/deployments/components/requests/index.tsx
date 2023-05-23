import { FC, useMemo, useState } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { Alert, Col, Row } from "antd";
import { SchemaForm } from "@lepton-dashboard/routers/deployments/components/schema-form";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any.ts";

export const Requests: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const [result, setResult] = useState<SafeAny>("output should appear here");
  const schema = photon?.openapi_schema?.components?.schemas?.Run_handlerInput;
  const exampleData =
    photon?.openapi_schema?.paths?.["/run"]?.post?.requestBody?.content?.[
      "application/json"
    ]?.example;
  const displayResult = useMemo(() => {
    if (typeof result === "string") {
      return result;
    } else if (typeof result === "object") {
      return JSON.stringify(result);
    } else {
      return "outputs format not supported";
    }
  }, [result]);
  return schema ? (
    <Row gutter={[32, 16]}>
      <Col flex="1 0 400px">
        <SchemaForm
          deployment={deployment}
          initData={exampleData}
          resultChange={setResult}
          schema={schema}
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
