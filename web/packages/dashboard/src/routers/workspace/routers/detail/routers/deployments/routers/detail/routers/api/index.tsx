import { FC, useEffect, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Segmented, Space, Typography } from "antd";
import { css } from "@emotion/react";
import {
  LeptonAPIItem,
  OpenApiService,
} from "@lepton-dashboard/services/open-api.service";
import {
  CodeBlock,
  createStringLiteralSecretTokenMasker,
} from "@lepton/ui/components/code-block";
import { ApiItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api/components/api-item";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { Link } from "@lepton-dashboard/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";

type CodeLanguage = "python" | "bash";

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const [initialized, setInitialized] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState<CodeLanguage>("python");
  const [apis, setApis] = useState<LeptonAPIItem[]>([]);
  const photons = useStateFromBehaviorSubject(photonService.list());
  const photon = useMemo(() => {
    return photons.find((p) => p.id === deployment.photon_id);
  }, [deployment.photon_id, photons]);

  useEffect(() => {
    const parseSchema = async () => {
      if (photon?.openapi_schema) {
        const url = deployment.status.endpoint.external_endpoint;
        const res = await openApiService.parse({
          ...photon.openapi_schema,
          servers:
            photon.openapi_schema?.servers?.length > 0
              ? photon.openapi_schema.servers
              : [{ url }],
        });
        const apis = res ? openApiService.convertToLeptonAPIItems(res) : [];
        setApis(apis);
      }
      setInitialized(true);
    };
    parseSchema().then();
  }, [deployment, openApiService, photon, setApis]);

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

  return initialized ? (
    <Card
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
                      value: "python",
                    },
                    {
                      label: "HTTP",
                      value: "bash",
                    },
                  ]}
                  value={codeLanguage}
                  onChange={(e) => setCodeLanguage(e as CodeLanguage)}
                />
              </Space>
            </Col>
          </Row>
          {codeLanguage === "python" && (
            <>
              <Typography.Paragraph>
                Install the Python client:
              </Typography.Paragraph>
              <Typography.Paragraph>
                <CodeBlock
                  code="pip install leptonai"
                  language="bash"
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
                  language="python"
                  tokenMask={createStringLiteralSecretTokenMasker(
                    APIToken || "",
                    {
                      startAt: 3,
                      endAt: 3,
                    }
                  )}
                  copyable
                />
              </Typography.Paragraph>
            </>
          )}
          {APIToken && codeLanguage === "bash" && (
            <>
              <Typography.Paragraph>
                Export your API token as an environment variable:
              </Typography.Paragraph>
              <Typography.Paragraph>
                <CodeBlock
                  code={`export LEPTON_API_TOKEN="${APIToken}"`}
                  language="bash"
                  tokenMask={createStringLiteralSecretTokenMasker(
                    APIToken || "",
                    {
                      startAt: 3,
                      endAt: 3,
                    }
                  )}
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
          {codeLanguage === "python" && (
            <Typography.Paragraph>
              Then, you can call the API(s) like the following code segments:
            </Typography.Paragraph>
          )}
          {codeLanguage === "bash" &&
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
          {codeLanguage === "bash" && isPublic && (
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
  ) : null;
};
