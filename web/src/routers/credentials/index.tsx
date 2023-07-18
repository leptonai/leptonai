import { useInject } from "@lepton-libs/di";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import styled from "@emotion/styled";
import { Table, Typography } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { CopyFile } from "@carbon/icons-react";

const Container = styled.div`
  padding: 32px;
`;

export const Credentials = () => {
  const authService = useInject(AuthService);
  const workspaces = useStateFromObservable(
    () => authService.listAuthorizedWorkspaces(),
    []
  );
  return (
    <Container>
      <Typography.Title level={2}>Credentials</Typography.Title>
      <Table
        pagination={false}
        size="small"
        bordered
        dataSource={workspaces}
        columns={[
          {
            title: "Workspace Name",
            dataIndex: "displayName",
          },
          {
            title: "Credentials",
            dataIndex: "token",
            render: (v, record) => (
              <Typography.Text
                copyable={{
                  icon: <CarbonIcon icon={<CopyFile />} />,
                  text: `${record.id}:${v}`,
                }}
              >
                ••••••••••••
              </Typography.Text>
            ),
          },
        ]}
      />
    </Container>
  );
};
