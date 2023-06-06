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
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";

const ApiItem: FC<{
  api: LeptonAPIItem;
}> = ({ api }) => {
  const theme = useAntdTheme();
  const openApiService = useInject(OpenApiService);

  const curl = useMemo(() => {
    if (api.request) {
      return openApiService.curlify(api.request);
    } else {
      return "";
    }
  }, [api.request, openApiService]);

  return (
    <Card paddingless shadowless borderless>
      <Divider
        style={{ marginTop: 0 }}
        orientation="left"
        orientationMargin={0}
      >
        {api.operation.path}
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
        <Typography.Paragraph copyable={{ text: curl }}>
          <pre
            css={css`
              margin: 0 !important;
              font-family: ${theme.fontFamily} !important;
              background: ${theme.colorBgLayout} !important;
              padding: 16px !important;
              color: ${theme.colorTextSecondary} !important;
            `}
          >
            {curl}
          </pre>
        </Typography.Paragraph>
      </div>
    </Card>
  );
};

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const apis = useStateFromObservable(
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
    []
  );

  return (
    <Card shadowless borderless>
      {apis.length > 0 ? (
        <>
          {apis.map((api) => (
            <ApiItem api={api} key={api.operationId} />
          ))}
        </>
      ) : (
        <Alert showIcon type="warning" message="No openapi schema found" />
      )}
    </Card>
  );
};
