import { FC, useCallback, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Segmented, Space, Typography } from "antd";
import { css } from "@emotion/react";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";
import {
  CodeBlock,
  LanguageSupports,
} from "@lepton-dashboard/routers/workspace/components/code-block";
import { ApiItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api/components/api-item";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { Link } from "@lepton-dashboard/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const [loading, setLoading] = useState(true);
  const [codeLanguage, setCodeLanguage] = useState<LanguageSupports>(
    LanguageSupports.Python
  );
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

  const isPublic = useMemo(() => {
    return !deployment.api_tokens?.length;
  }, [deployment]);

  const docsUrl = useMemo(() => {
    const url = deployment.status.endpoint.external_endpoint;
    return `${url}/docs`;
  }, [deployment]);

  const APIToken = useMemo(() => {
    return workspaceTrackerService.workspace?.auth.token ?? "";
  }, [workspaceTrackerService.workspace?.auth.token]);

  const maskToken = useCallback(
    (content: string) => {
      if (APIToken && content.includes(APIToken)) {
        const startSubstring = APIToken.substring(0, 3);
        const endSubstring = APIToken.substring(
          APIToken.length - 3,
          APIToken.length
        );
        return `"${startSubstring}${"*".repeat(
          APIToken.length - 6
        )}${endSubstring}"`;
      } else {
        return false;
      }
    },
    [APIToken]
  );
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
          <Row justify="space-between">
            <Col>
              <Typography.Title
                css={css`
                  margin: 0;
                  padding: 4px 0;
                `}
                level={5}
              >
                Call the API
              </Typography.Title>
            </Col>
            <Col>
              <Space>
                <Segmented
                  options={[
                    {
                      label: "Python",
                      value: LanguageSupports.Python,
                    },
                    {
                      label: "HTTP",
                      value: LanguageSupports.Bash,
                    },
                  ]}
                  value={codeLanguage}
                  onChange={(e) => setCodeLanguage(e as LanguageSupports)}
                />
              </Space>
            </Col>
          </Row>
          {codeLanguage === LanguageSupports.Python && (
            <>
              <Typography.Paragraph>
                Install the Python client:
              </Typography.Paragraph>
              <Typography.Paragraph>
                <CodeBlock
                  code="pip install leptonai"
                  language={LanguageSupports.Bash}
                  copyable
                />
              </Typography.Paragraph>
              {APIToken ? (
                <Typography.Paragraph>
                  Import the client and save your API token as a variable:
                </Typography.Paragraph>
              ) : (
                <Typography.Paragraph>Import the client:</Typography.Paragraph>
              )}

              <Typography.Paragraph>
                <CodeBlock
                  code={
                    APIToken
                      ? `from leptonai.client import Client
LEPTON_API_TOKEN = "${APIToken}"`
                      : `from leptonai.client import Client`
                  }
                  language={LanguageSupports.Python}
                  tokenMask={maskToken}
                  copyable
                />
              </Typography.Paragraph>
            </>
          )}
          {APIToken && codeLanguage === LanguageSupports.Bash && (
            <>
              <Typography.Paragraph>
                Export your API token as an environment variable:
              </Typography.Paragraph>
              <Typography.Paragraph>
                <CodeBlock
                  code={`export LEPTON_API_TOKEN="${APIToken}"`}
                  language={LanguageSupports.Bash}
                  tokenMask={maskToken}
                  copyable
                />
              </Typography.Paragraph>
            </>
          )}
          {APIToken && (
            <Typography.Paragraph>
              You can find your API token in the{" "}
              <LinkTo
                css={css`
                  text-decoration: underline !important;
                `}
                name="settingsAPITokens"
              >
                settings page
              </LinkTo>
              .
            </Typography.Paragraph>
          )}
          {codeLanguage === LanguageSupports.Python && (
            <Typography.Paragraph>
              Then, you can call the API(s) like the following code segments:
            </Typography.Paragraph>
          )}
          {codeLanguage === LanguageSupports.Bash &&
            (APIToken ? (
              <Typography.Paragraph>
                Then, you can call the API(s) with cURL like the following code
                segments:
              </Typography.Paragraph>
            ) : (
              <Typography.Paragraph>
                You can call the API(s) with cURL like the following code
                segments:
              </Typography.Paragraph>
            ))}
          {apis.map((api) => (
            <ApiItem
              api={api}
              authorization={APIToken}
              key={api.operationId}
              deployment={deployment}
              language={codeLanguage}
            />
          ))}
          {codeLanguage === LanguageSupports.Bash && isPublic && (
            <>
              <br />
              You can also check{" "}
              <Link
                css={css`
                  text-decoration: underline !important;
                `}
                to={docsUrl}
                target="_blank"
              >
                API docs here.
              </Link>
            </>
          )}
        </>
      ) : (
        <Alert showIcon type="warning" message="No openapi schema found" />
      )}
    </Card>
  );
};
