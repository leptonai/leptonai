import { CopyFile, Settings, Upgrade, WordCloud } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/components/card";
import { Quotas } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/general/quotas";
import { WorkspaceService } from "@lepton-dashboard/routers/workspace/services/workspace.service";

import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Button, Col, Collapse, Descriptions, Row, Typography } from "antd";
import { FC, useState } from "react";

export const General: FC = () => {
  const [loading, setLoading] = useState(true);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const workspaceService = useInject(WorkspaceService);
  const workspaceDetail = useStateFromObservable(
    () => workspaceService.getWorkspaceDetail(),
    null,
    { next: () => setLoading(false), error: () => setLoading(false) }
  );
  const theme = useAntdTheme();
  return (
    <MinThemeProvider hideBorder={false}>
      <Card
        loading={loading}
        icon={<CarbonIcon icon={<Settings />} />}
        borderless
        shadowless
        title="General"
      >
        <Card
          shadowless
          paddingless
          css={css`
            margin-bottom: 16px;
          `}
        >
          <Row
            css={css`
              padding: 16px 16px 12px 16px;
            `}
            gutter={[16, 16]}
            justify="space-between"
          >
            <Col flex={0}>
              <Typography.Title
                level={4}
                css={css`
                  margin-top: 0;
                `}
              >
                <span
                  css={css`
                    margin-right: 8px;
                  `}
                >
                  <CarbonIcon icon={<WordCloud />} />
                </span>{" "}
                Basic plan
              </Typography.Title>
              <Typography.Text type="secondary">
                For individuals and small teams who are just getting started
              </Typography.Text>
            </Col>
            <Col flex={0}>
              <Button
                type="primary"
                size="small"
                href="mailto:info@lepton.ai"
                icon={<CarbonIcon icon={<Upgrade />} />}
              >
                Contact us to upgrade
              </Button>
            </Col>
          </Row>
          {workspaceDetail && (
            <div
              css={css`
                padding: 12px 16px 16px 16px;
                border-top: 1px dashed ${theme.colorBorderSecondary};
              `}
            >
              <Quotas workspaceDetail={workspaceDetail} />
            </div>
          )}
        </Card>

        <Collapse
          defaultActiveKey={[0]}
          size="small"
          css={css`
            background: transparent;
            .ant-collapse-content-box {
              padding: 0 !important;
            }
          `}
          items={[
            {
              key: 0,
              label: "Settings",
              children: (
                <Descriptions
                  column={1}
                  bordered
                  size="small"
                  css={css`
                    .ant-descriptions-view {
                      border: none !important;
                    }
                  `}
                  labelStyle={{
                    fontWeight: 500,
                    width: "70px",
                    color: theme.colorTextHeading,
                  }}
                >
                  <Descriptions.Item label="ID">
                    <Typography.Text
                      copyable={{
                        icon: <CarbonIcon icon={<CopyFile />} />,
                      }}
                    >
                      {workspaceTrackerService.workspace?.auth.id}
                    </Typography.Text>
                  </Descriptions.Item>
                  {workspaceTrackerService.workspace?.auth.displayName && (
                    <Descriptions.Item label="Name">
                      <Typography.Text
                        copyable={{
                          icon: <CarbonIcon icon={<CopyFile />} />,
                        }}
                      >
                        {workspaceTrackerService.workspace?.auth.displayName}
                      </Typography.Text>
                    </Descriptions.Item>
                  )}

                  {workspaceDetail && (
                    <>
                      <Descriptions.Item label="Version">
                        <Typography.Text
                          copyable={{
                            icon: <CarbonIcon icon={<CopyFile />} />,
                          }}
                        >
                          {workspaceDetail?.git_commit}
                        </Typography.Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="Date">
                        <Typography.Text
                          copyable={{
                            icon: <CarbonIcon icon={<CopyFile />} />,
                          }}
                        >
                          {workspaceDetail?.build_time}
                        </Typography.Text>
                      </Descriptions.Item>
                      {workspaceDetail?.workspace_state && (
                        <Descriptions.Item label="State">
                          <Typography.Text
                            copyable={{
                              icon: <CarbonIcon icon={<CopyFile />} />,
                            }}
                          >
                            {workspaceDetail?.workspace_state}
                          </Typography.Text>
                        </Descriptions.Item>
                      )}
                    </>
                  )}
                </Descriptions>
              ),
            },
          ]}
        />
      </Card>
    </MinThemeProvider>
  );
};
