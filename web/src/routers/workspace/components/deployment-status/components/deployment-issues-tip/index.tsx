import { FC, PropsWithChildren, useMemo, useState } from "react";
import { Popover } from "antd";
import { State } from "@lepton-dashboard/interfaces/deployment";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { combineLatest, filter, switchMap, takeUntil } from "rxjs";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";

export const DeploymentIssuesTip: FC<
  { status: string; deploymentId: string } & PropsWithChildren
> = ({ status, deploymentId, children }) => {
  const deploymentService = useInject(DeploymentService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const status$ = useObservableFromState(status);
  const deploymentId$ = useObservableFromState(deploymentId);
  const hovered$ = useObservableFromState(hovered);

  const readiness = useStateFromObservable(
    () =>
      combineLatest([status$, hovered$, deploymentId$]).pipe(
        filter(([status, hovered, _]) => hovered && status !== State.Running),
        switchMap(([_, __, deploymentId]) => {
          return deploymentService
            .getReadiness(deploymentId)
            .pipe(takeUntil(hovered$.pipe(filter((hovered) => !hovered))));
        })
      ),
    {},
    {
      next: (data) => {
        const hasIssues = Object.entries(data).some(([_, value]) =>
          value.some((e) => !!e.message)
        );
        setOpen(hasIssues);
        setHovered(hasIssues);
      },
      error: () => {
        setHovered(false);
        setOpen(false);
      },
    }
  );

  const message = useMemo(() => {
    let issuesCount = 0;
    let replicasCount = 0;
    Object.entries(readiness).forEach(([_, value]) => {
      const issues = value.filter((e) => !!e.message);
      if (issues.length > 0) {
        replicasCount++;
        issuesCount += issues.length;
      }
    });

    if (issuesCount === 0) {
      return "";
    }

    let message: string;
    if (issuesCount === 1) {
      message = "1 issue in ";
    } else {
      message = `${issuesCount} issues in `;
    }
    if (replicasCount === 1) {
      message += "1 replica";
    } else {
      message += `${replicasCount} replicas`;
    }

    return (
      <Link
        to={`/workspace/${workspaceTrackerService.name}/deployments/detail/${deploymentId}/replicas/list`}
        relative="route"
        underline
      >
        Found {message}, view details in the replicas list.
      </Link>
    );
  }, [readiness, workspaceTrackerService.name, deploymentId]);

  if (status !== State.Running) {
    return (
      <Popover
        placement="bottomLeft"
        open={open}
        onOpenChange={(open) => {
          setHovered(open);
          if (!open) {
            setOpen(false);
          }
        }}
        content={<div onClick={(e) => e.stopPropagation()}>{message}</div>}
      >
        <span>{children}</span>
      </Popover>
    );
  } else {
    return <>{children}</>;
  }
};
