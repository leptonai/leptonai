import { FC, useMemo, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Segmented, Space, Typography } from "antd";
import { css } from "@emotion/react";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import {
  LanguageSupports,
  SyntaxHighlight,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api/components/syntax-highlight";
import { ApiItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api/components/api-item";

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
  const [loading, setLoading] = useState(true);
  const [codeLanguage, setCodeLanguage] = useState<LanguageSupports>(
    LanguageSupports.Python
  );
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

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
            <Typography>
              <Typography.Paragraph>
                Install the Python client:
              </Typography.Paragraph>
              <SyntaxHighlight
                code="pip install leptonai"
                language={LanguageSupports.Bash}
              />
            </Typography>
          )}
          <Typography.Paragraph>
            Replace the <Typography.Text code>$YOUR_TOKEN</Typography.Text> in
            the following code segment with{" "}
            <Link
              css={css`
                text-decoration: underline !important;
              `}
              to={`/workspace/${workspaceTrackerService.name}/settings/api-tokens`}
            >
              your API token
            </Link>
            .
          </Typography.Paragraph>
          {apis.map((api) => (
            <ApiItem
              api={api}
              key={api.operationId}
              deployment={deployment}
              language={codeLanguage}
            />
          ))}
          {codeLanguage === LanguageSupports.Bash && (
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
