import { FC, useMemo } from "react";
import {
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { Typography } from "antd";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { CopyFile } from "@carbon/icons-react";
import {
  LanguageSupports,
  SyntaxHighlight,
} from "../../../../components/syntax-highlight";

export const ApiItem: FC<{
  api: LeptonAPIItem;
  deployment: Deployment;
  language: LanguageSupports;
}> = ({ api, deployment, language }) => {
  const openApiService = useInject(OpenApiService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

  const code = useMemo(() => {
    if (api.request) {
      const hasAuthHeader = Object.hasOwn(api.request.headers, "Authorization");
      switch (language) {
        case LanguageSupports.Python:
          if (import.meta.env.VITE_ENABLE_OAUTH === "enable") {
            return openApiService.toPythonSDKCode(api, {
              deployment: deployment.name,
              workspace: workspaceTrackerService.name || "",
            });
          } else {
            return openApiService.toPythonSDKCode(
              api,
              import.meta.env.VITE_WORKSPACE_URL
            );
          }

        case LanguageSupports.Bash:
          return openApiService.curlify({
            ...api.request,
            headers: hasAuthHeader
              ? api.request.headers
              : {
                  ...api.request.headers,
                  Authorization: "Bearer $YOUR_TOKEN",
                },
          });
        default:
          return "";
      }
    } else {
      return "";
    }
  }, [language, api, deployment, openApiService, workspaceTrackerService]);

  return (
    <>
      <Typography.Paragraph strong>{api.operation.path}</Typography.Paragraph>
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
          copyable={{ text: code, icon: <CarbonIcon icon={<CopyFile />} /> }}
        >
          <SyntaxHighlight code={code} language={language} />
        </Typography.Paragraph>
      </div>
    </>
  );
};
