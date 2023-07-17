import { FC, useMemo } from "react";
import {
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { Typography } from "antd";
import { LanguageSupports, CodeBlock } from "../../../../components/code-block";

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
              workspace: workspaceTrackerService.id || "",
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
      <Typography.Paragraph>
        <CodeBlock code={code} language={language} copyable />
      </Typography.Paragraph>
    </>
  );
};
