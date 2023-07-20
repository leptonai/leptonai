import {
  DeploymentReadinessItem,
  ReadinessReason,
  ReplicaTermination,
} from "@lepton-dashboard/interfaces/deployment";
import { Popover, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { useMemo } from "react";
import { css } from "@emotion/react";
import { ExclamationCircleFilled } from "@ant-design/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

const ReadinessStatusTag = ({ item }: { item: DeploymentReadinessItem }) => {
  const color = useMemo(() => {
    switch (item.reason) {
      case ReadinessReason.ReadinessReasonReady:
        return "success";
      case ReadinessReason.ReadinessReasonInProgress:
        return "processing";
      case ReadinessReason.ReadinessReasonNoCapacity:
        return "warning";
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
  terminations,
}: {
  readiness?: DeploymentReadinessItem[];
  terminations?: ReplicaTermination[];
}) => {
  const theme = useAntdTheme();
  const readyCount = readiness?.filter(
    (item) => item.reason === ReadinessReason.ReadinessReasonReady
  ).length;
  let readinessPart: JSX.Element | null = null;
  let terminationsPart: JSX.Element | null = null;
  if (readiness && readiness.length > 0) {
    readinessPart = (
      <>
        <tr>
          <th colSpan={4}>
            {readyCount} out of {readiness.length} replicas ready
          </th>
        </tr>
        <tr>
          <th colSpan={2}>status</th>
          <th colSpan={2}>message</th>
        </tr>
        {readiness.map((item, index) => (
          <tr key={`status-readiness-${index}`}>
            <td colSpan={2}>
              <ReadinessStatusTag item={item} />
            </td>
            <td colSpan={2}>
              {item.message || (
                <Typography.Text type="secondary">(empty)</Typography.Text>
              )}
            </td>
          </tr>
        ))}
      </>
    );
  }
  if (terminations && terminations.length > 0) {
    terminationsPart = (
      <>
        <tr>
          <th colSpan={4}>There are earlier terminations</th>
        </tr>
        <tr>
          <th>start</th>
          <th>end time</th>
          <th>reason (exit code)</th>
          <th>message</th>
        </tr>
        {terminations.map((termination, index) => (
          <tr key={`status-termination-${index}`}>
            <td width={180}>
              {dayjs(termination.started_at * 1000).format(
                "MMM D, YYYY h:mm:ss A"
              )}
            </td>
            <td width={180}>
              {dayjs(termination.finished_at * 1000).format(
                "MMM D, YYYY h:mm:ss A"
              )}
            </td>
            <td width={130}>
              {termination.reason} ({termination.exit_code})
            </td>
            <td>
              {termination.message || (
                <Typography.Text type="secondary">(empty)</Typography.Text>
              )}
            </td>
          </tr>
        ))}
      </>
    );
  }

  return (
    <table
      css={css`
        width: 100%;
        border-collapse: collapse;
        border-spacing: 0;
        th,
        td {
          padding: ${theme.paddingXS}px;
          border-bottom: 1px solid ${theme.colorBorder};
          white-space: pre-wrap;
        }
        tr:last-child td {
          border-bottom: none;
        }
        th {
          text-align: left;
        }
      `}
    >
      <tbody>
        {readinessPart}
        {terminationsPart}
      </tbody>
    </table>
  );
};
export const StatusPopover = ({
  readiness,
  terminations,
}: {
  readiness?: DeploymentReadinessItem[];
  terminations?: ReplicaTermination[];
}) => {
  const hasReadiness =
    readiness &&
    readiness.length > 0 &&
    readiness.some(
      (item) => item.reason !== ReadinessReason.ReadinessReasonReady
    );
  const hasTerminations = terminations && terminations.length > 0;
  if (!hasReadiness && !hasTerminations) {
    return null;
  }
  return (
    <Popover
      content={
        <div
          css={css`
            max-width: 50vw;
            min-width: 300px;
          `}
        >
          <ReplicaStatusTable
            readiness={readiness}
            terminations={terminations}
          />
        </div>
      }
    >
      <Typography.Text type={hasTerminations ? "warning" : "secondary"}>
        <ExclamationCircleFilled />
      </Typography.Text>
    </Popover>
  );
};
