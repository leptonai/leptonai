import { FC } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { JsonSchemaService } from "@lepton-dashboard/services/json-schema.service";
import { Alert, Divider, Typography } from "antd";
import { css } from "@emotion/react";
import { Photon } from "@lepton-dashboard/interfaces/photon";

const ApiItem: FC<{
  path: string;
  photon?: Photon;
  deployment: Deployment;
}> = ({ path, photon, deployment }) => {
  const theme = useAntdTheme();
  const url = deployment.status.endpoint.external_endpoint;
  const jsonSchemaService = useInject(JsonSchemaService);
  const { inputExample } = jsonSchemaService.parse(
    photon?.openapi_schema,
    path
  );
  const exampleString = inputExample ? JSON.stringify(inputExample) : "";
  const queryText = `curl -s -X POST \\
  -d '${exampleString}' \\
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
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const jsonSchemaService = useInject(JsonSchemaService);
  const paths = jsonSchemaService.getPaths(photon?.openapi_schema);

  return (
    <Card shadowless borderless>
      {paths.length > 0 ? (
        <>
          {paths.map((p) => (
            <ApiItem path={p} key={p} deployment={deployment} photon={photon} />
          ))}
        </>
      ) : (
        <Alert showIcon type="warning" message="No openapi schema found" />
      )}
    </Card>
  );
};
