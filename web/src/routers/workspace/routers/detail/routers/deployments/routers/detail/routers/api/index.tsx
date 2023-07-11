import { FC, useState } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Alert, Col, Row, Segmented, Space, Typography } from "antd";
import { css } from "@emotion/react";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
import { from, of, switchMap } from "rxjs";
import { LanguageSupports, CodeBlock } from "../../components/code-block";
import { ApiItem } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api/components/api-item";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const Api: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const photonService = useInject(PhotonService);
  const openApiService = useInject(OpenApiService);
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
            </>
          )}
          <Typography.Paragraph>
            Replace the <Typography.Text code>$YOUR_TOKEN</Typography.Text> in
            the following code segment with{" "}
            <LinkTo
              css={css`
                text-decoration: underline !important;
              `}
              name="settingsAPITokens"
            >
              your API token
            </LinkTo>
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
        </>
      ) : (
        <Alert showIcon type="warning" message="No openapi schema found" />
      )}
    </Card>
  );
};
