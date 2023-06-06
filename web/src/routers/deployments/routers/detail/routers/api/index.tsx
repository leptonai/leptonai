import { FC, useMemo } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Divider, Typography } from "antd";
import { css } from "@emotion/react";
import {
  OpenApiService,
  OperationWithPath,
} from "@lepton-dashboard/services/open-api.service";
import { from, map, switchMap } from "rxjs";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

const ApiItem: FC<{
  path: string;
  operation: OperationWithPath;
  deployment: Deployment;
}> = ({ path, operation, deployment }) => {
  const theme = useAntdTheme();
  const openApiService = useInject(OpenApiService);
  const url = deployment.status.endpoint.external_endpoint;

  const request = useMemo(() => {
    const contents = openApiService.listMediaTypeObjects(operation);
    let requestBody: SafeAny = null;
    if (contents["application/json"]) {
      requestBody = openApiService.sampleFromSchema(
        contents["application/json"].schema,
        contents["application/json"].example
      );
    }
    return {
      body: requestBody,
    };
  }, [openApiService, operation]);

  const dataString = request?.body ? JSON.stringify(request.body) : "";
  const queryText = `curl -s -X POST \\
  -d '${dataString}' \\
  -H 'deployment: ${deployment.name}' \\
  -H 'Content-Type: application/json' \\
  "${url}${path}"`;
  return (
    <Card paddingless shadowless borderless>
      <Divider
        style={{ marginTop: 0 }}
        orientation="left"
        orientationMargin={0}
      >
        {path}
      </Divider>
      <div
        css={css`
          position: relative;
          .ant-typography-copy {
            position: absolute;
            top: 8px;
            right: 8px;
          }
        `}
      >
        <Typography.Paragraph copyable={{ text: queryText }}>
          <pre
            css={css`
              margin: 0 !important;
              font-family: ${theme.fontFamily} !important;
              background: ${theme.colorBgLayout} !important;
              padding: 16px !important;
              color: ${theme.colorTextSecondary} !important;
            `}
          >
            {queryText}
          </pre>
        </Typography.Paragraph>
      </div>
    </Card>
  );
};

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const operations = useStateFromObservable(
    () =>
      photonService.id(deployment.photon_id).pipe(
        switchMap((p) => {
          if (p?.openapi_schema) {
            return from(openApiService.parse(p.openapi_schema));
          }
          return from(Promise.resolve(null));
        }),
        map((schema) => {
          if (schema) {
            return openApiService.listOperations(schema);
          } else {
            return [];
          }
        })
      ),
    []
  );

  return (
    <Card shadowless borderless>
      {operations.length > 0 ? (
        <>
          {operations.map((operation) => (
            <ApiItem
              path={operation.path}
              key={operation.operationId}
              deployment={deployment}
              operation={operation}
            />
          ))}
        </>
      ) : (
        <Alert showIcon type="warning" message="No openapi schema found" />
      )}
    </Card>
  );
};
