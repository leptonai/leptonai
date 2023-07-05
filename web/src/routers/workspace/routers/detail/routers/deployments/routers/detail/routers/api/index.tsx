import { CopyFile, Launch } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { FC, useMemo, useState } from "react";
import { Card } from "../../../../../../../../../../components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Button, Divider, Typography } from "antd";
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
      const hasAuthHeader = Object.hasOwn(api.request.headers, "Authorization");
      return openApiService.curlify({
        ...api.request,
        headers: hasAuthHeader
          ? api.request.headers
          : {
              ...api.request.headers,
              Authorization: "Bearer $YOUR_TOKEN",
            },
      });
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
        <Typography.Paragraph
          copyable={{ text: curl, icon: <CarbonIcon icon={<CopyFile />} /> }}
        >
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
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const [loading, setLoading] = useState(true);

  const apis = useStateFromObservable(
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
                .then((res) =>
                  res ? openApiService.convertToLeptonAPIItems(res) : []
                )
            );
          }
          return of([]);
        })
      ),
    [],
    {
      next: () => setLoading(false),
      error: () => setLoading(false),
    }
  );

  const docsUrl = useMemo(() => {
    const url = deployment.status.endpoint.external_endpoint;
    return `${url}/docs`;
  }, [deployment]);

  return (
    <Card
      loading={loading}
      shadowless
      borderless
      css={css`
        position: relative;
      `}
    >
      {apis.length > 0 ? (
        <>
          <Button
            size="small"
            type="default"
            icon={<CarbonIcon icon={<Launch />} />}
            href={docsUrl}
            target="_blank"
            css={css`
              position: absolute;
              right: 16px;
              top: auto;
              z-index: 2;
              &::before {
                content: "";
                display: block;
                width: 1em;
                height: 100%;
                background: ${theme.colorBgContainer};
                position: absolute;
                left: -1em;
                margin-left: -1px;
              }
            `}
          >
            API Docs
          </Button>
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
