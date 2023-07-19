import { FC, PropsWithChildren, useMemo, useState } from "react";
import { Popover } from "antd";
import {
  ReadinessReason,
  State,
} from "@lepton-dashboard/interfaces/deployment";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { combineLatest, filter, switchMap, takeUntil } from "rxjs";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const DeploymentIssuesTip: FC<
  { status: string; deploymentName: string } & PropsWithChildren
> = ({ status, deploymentName, children }) => {
  const deploymentService = useInject(DeploymentService);
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const status$ = useObservableFromState(status);
  const deploymentName$ = useObservableFromState(deploymentName);
  const hovered$ = useObservableFromState(hovered);

  const readiness = useStateFromObservable(
    () =>
      combineLatest([status$, hovered$, deploymentName$]).pipe(
        filter(([status, hovered, _]) => hovered && status !== State.Running),
        switchMap(([_, __, deploymentName]) => {
          return deploymentService
            .getReadiness(deploymentName)
            .pipe(takeUntil(hovered$.pipe(filter((hovered) => !hovered))));
        })
      ),
    {},
    {
      next: (data) => {
        const hasIssues = Object.entries(data).some(([_, value]) =>
          value.some((e) => e.reason !== ReadinessReason.ReadinessReasonReady)
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
      const issues = value.filter(
        (e) => e.reason !== ReadinessReason.ReadinessReasonReady
      );
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
      <LinkTo
        name="deploymentDetailReplicasList"
        params={{ deploymentName }}
        relative="route"
        underline
      >
        Found {message}, view details in the replicas list
      </LinkTo>
    );
  }, [readiness, deploymentName]);

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
