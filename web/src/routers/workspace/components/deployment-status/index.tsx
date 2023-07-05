import { FC, useMemo } from "react";
import { Tag } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { css } from "@emotion/react";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { State } from "@lepton-dashboard/interfaces/deployment";
import { DeploymentIssuesTip } from "@lepton-dashboard/routers/workspace/components/deployment-status/components/deployment-issues-tip";

export const DeploymentStatus: FC<
  { deploymentId: string; status: State | string } & EmotionProps
> = ({ status, deploymentId, className }) => {
  const color = useMemo(() => {
    switch (status) {
      case State.Running:
        return "success";
      case State.NotReady:
        return "warning";
      default:
        return "processing";
    }
  }, [status]);
  return (
    <DeploymentIssuesTip status={status} deploymentId={deploymentId}>
      <Tag
        className={className}
        css={css`
          margin-inline: 0;
          font-weight: 500;
        `}
        icon={<DeploymentIcon />}
        color={color}
      >
        {status.toUpperCase()}
      </Tag>
    </DeploymentIssuesTip>
  );
};
