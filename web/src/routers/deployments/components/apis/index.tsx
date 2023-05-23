import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Typography } from "antd";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const Apis: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const theme = useAntdTheme();
  const url = deployment.status.endpoint.external_endpoint;
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const example =
    photon?.openapi_schema?.paths?.["/run"]?.post?.requestBody?.content?.[
      "application/json"
    ]?.example;
  const exampleString = example ? JSON.stringify(example) : "";
  const queryText = `curl -s -X POST \\
  -d '${exampleString}' \\
  -H 'Content-Type: application/json' \\
  "${url}/run"`;
  return (
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
  );
};
