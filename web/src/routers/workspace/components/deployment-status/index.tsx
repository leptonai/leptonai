import { FC, useMemo, useState } from "react";
import { Tag } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { css } from "@emotion/react";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import {
  DeploymentReadiness,
  State,
} from "@lepton-dashboard/interfaces/deployment";
import { DeploymentIssuesTip } from "@lepton-dashboard/routers/workspace/components/deployment-status/components/deployment-issues-tip";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { combineLatest, filter, of, switchMap, takeUntil } from "rxjs";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { LoadingOutlined } from "@ant-design/icons";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";

export const DeploymentStatus: FC<
  { deploymentId: string; status: State | string } & EmotionProps
> = ({ status, deploymentId, className }) => {
  const deploymentService = useInject(DeploymentService);
  const refreshService = useInject(RefreshService);
  const status$ = useObservableFromState(status);
  const deploymentId$ = useObservableFromState(deploymentId);
  const [loading, setLoading] = useState(false);

  const readiness = useStateFromObservable(
    () =>
      combineLatest([status$, deploymentId$]).pipe(
        switchMap(([status, deploymentId]) => {
          setLoading(status === State.NotReady);
          return status === State.NotReady
            ? refreshService.refresh$.pipe(
                switchMap(() => {
                  return deploymentService.getReadiness(deploymentId);
                }),
                takeUntil(
                  status$.pipe(filter((status) => status !== State.NotReady))
                )
              )
            : of({} as DeploymentReadiness);
        })
      ),
    {},
    {
      next: () => {
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  const hasIssues = useMemo(
    () => Object.entries(readiness).some(([_, value]) => value.length > 0),
    [readiness]
  );

  return (
    <DeploymentIssuesTip status={status} readiness={readiness}>
      <Tag
        className={className}
        bordered={false}
        css={css`
          margin-inline: 0;
          font-weight: 500;
        `}
        icon={loading ? <LoadingOutlined /> : <DeploymentIcon />}
        color={
          status === State.Running
            ? "success"
            : hasIssues
            ? "warning"
            : "processing"
        }
      >
        {status.toUpperCase()}
      </Tag>
    </DeploymentIssuesTip>
  );
};
