import { css } from "@emotion/react";
import { useInject } from "@lepton-libs/di";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Table, Typography } from "antd";
import { CarbonIcon, LeptonIcon } from "@lepton-dashboard/components/icons";
import { CopyFile } from "@carbon/icons-react";

export const Credentials = () => {
  const authService = useInject(AuthService);
  const workspaces = useStateFromObservable(
    () => authService.listAuthorizedWorkspaces(),
    []
  );
  return (
    <div
      css={css`
        display: flex;
        justify-content: center;
        padding-top: 12%;
      `}
    >
      <div
        css={css`
          padding: 32px;
        `}
      >
        <Typography.Title
          level={2}
          css={css`
            margin-top: 0;
          `}
        >
          <LeptonIcon
            css={css`
              margin-right: 8px;
            `}
          />
          Credentials
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          You have the following workspaces available. Copy the credential
          string of the workspace you want to log in, and paste it in the
          commandline.
        </Typography.Paragraph>
        <Table
          pagination={false}
          size="small"
          bordered
          dataSource={workspaces}
          rowKey="id"
          columns={[
            {
              title: "NAME",
              dataIndex: "displayName",
            },
            {
              title: "CREDENTIAL",
              dataIndex: "token",
              render: (v, record) => (
                <Typography.Text
                  copyable={{
                    icon: <CarbonIcon icon={<CopyFile />} />,
                  }}
                >
                  {record.id}:{v}
                </Typography.Text>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};
