import {
  DeploymentReadinessItem,
  ReadinessReason,
  ReplicaTermination,
} from "@lepton-dashboard/interfaces/deployment";
import { message, Popover, Table, Tag, Typography } from "antd";
import { ReactNode, useMemo } from "react";
import { css } from "@emotion/react";
import dayjs from "dayjs";

const copy = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    message.success("Copied");
  });
};

const ReadinessStatusTag = ({ item }: { item: DeploymentReadinessItem }) => {
  const color = useMemo(() => {
    switch (item.reason) {
      case ReadinessReason.ReadinessReasonReady:
        return "success";
      case ReadinessReason.ReadinessReasonInProgress:
        return "processing";
      case ReadinessReason.ReadinessReasonNoCapacity:
        return "warning";
      case ReadinessReason.ReadinessReasonDeploymentConfigError:
      case ReadinessReason.ReadinessReasonUserCodeError:
      case ReadinessReason.ReadinessReasonSystemError:
        return "error";
      case ReadinessReason.ReadinessReasonUnknown:
        return "default";
      default:
        return "default";
    }
  }, [item.reason]);

  return <Tag color={color}>{item.reason}</Tag>;
};
const ReplicaStatusTable = ({
  readiness,
}: {
  readiness?: DeploymentReadinessItem[];
}) => {
  return (
    <Table
      size="small"
      pagination={false}
      dataSource={readiness}
      columns={[
        {
          title: "Status",
          dataIndex: "reason",
          key: "reason",
          width: 150,
          render: (_, record) => <ReadinessStatusTag item={record} />,
        },
        {
          title: "Message",
          dataIndex: "message",
          key: "message",
          render: (message: string) =>
            message ? (
              <Typography.Text title={message} onClick={() => copy(message)}>
                {message}
              </Typography.Text>
            ) : (
              <Typography.Text type="secondary">(empty)</Typography.Text>
            ),
        },
      ]}
    />
  );
};

const TerminationsTable = ({
  terminations,
}: {
  terminations?: ReplicaTermination[];
}) => {
  return (
    <Table
      size="small"
      pagination={false}
      dataSource={terminations}
      columns={[
        {
          title: "Started At",
          dataIndex: "started_at",
          width: 180,
          render: (time) => dayjs(time * 1000).format("MMM D, YYYY h:mm:ss A"),
        },
        {
          title: "Finished At",
          dataIndex: "finished_at",
          width: 180,
          render: (time) => dayjs(time * 1000).format("MMM D, YYYY h:mm:ss A"),
        },
        {
          title: "Reason(exit code)",
          dataIndex: "reason",
          width: 150,
          render: (reason, record) => (
            <Typography.Text>
              {reason}({record.exit_code})
            </Typography.Text>
          ),
        },
        {
          title: "Message",
          dataIndex: "message",
          render: (message) =>
            message ? (
              <Typography.Text title={message} onClick={() => copy(message)}>
                {message}
              </Typography.Text>
            ) : (
              <Typography.Text type="secondary">(empty)</Typography.Text>
            ),
        },
      ]}
      footer={() =>
        terminations
          ? `There are ${terminations.length} earlier terminations`
          : null
      }
    />
  );
};

export const StatusPopover = ({
  readiness,
  children,
}: {
  readiness?: DeploymentReadinessItem[];
  children: ReactNode;
}) => {
  const hasReadiness = readiness && readiness.length > 0;
  if (!hasReadiness) {
    return <>{children}</>;
  }
  return (
    <Popover
      placement="bottomRight"
      content={
        <div
          css={css`
            max-width: 500px;
          `}
        >
          <ReplicaStatusTable readiness={readiness} />
        </div>
      }
    >
      <span
        css={css`
          cursor: default;
        `}
      >
        {children}
      </span>
    </Popover>
  );
};

export const TerminationsPopover = ({
  terminations,
  children,
}: {
  terminations?: ReplicaTermination[];
  children: ReactNode;
}) => {
  const hasTerminations = terminations && terminations.length > 0;
  if (!hasTerminations) {
    return <>{children}</>;
  }
  return (
    <Popover
      placement="bottomRight"
      content={
        <div
          css={css`
            max-width: 800px;
          `}
        >
          <TerminationsTable terminations={terminations} />
        </div>
      }
    >
      <span
        css={css`
          cursor: default;
        `}
      >
        {children}
      </span>
    </Popover>
  );
};
