import { ChatBot, Code, StopFilled } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { State } from "@lepton-dashboard/interfaces/deployment";
import {
  FineTuneJob,
  FineTuneJobStatus,
  TunaInference,
} from "@lepton-dashboard/interfaces/fine-tune";
import { ApiModal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/api-modal";
import { Terminate } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/terminate";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Button, Popconfirm, Space } from "antd";
import { FC, useCallback, useMemo, useState } from "react";

export const Actions: FC<{
  tuna: FineTuneJob;
  inference: TunaInference | null;
}> = ({ tuna, inference }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const navigateService = useInject(NavigateService);
  const tunaService = useInject(TunaService);
  const refreshService = useInject(RefreshService);
  const inferenceEnabled = inference?.status?.state === State.Running;

  const [deployLoading, setDeployLoading] = useState(false);

  const deployed = !!inference;

  const deployable = useMemo(() => {
    return [FineTuneJobStatus.SUCCESS].includes(tuna.status) && !deployed;
  }, [tuna.status, deployed]);

  const gotoModelComparison = useCallback(() => {
    navigateService.navigateTo("tunaChat", {
      name: `${inference!.metadata.name!}`,
    });
  }, [navigateService, inference]);

  const createDeployment = useCallback(() => {
    setDeployLoading(true);
    tunaService.createInference(tuna.name, tuna.output_dir).subscribe({
      next: () => {
        refreshService.refresh();
        setDeployLoading(false);
      },
      error: () => {
        refreshService.refresh();
        setDeployLoading(false);
      },
    });
  }, [tunaService, tuna.name, tuna.output_dir, refreshService]);

  const cancelable = useMemo(() => {
    return [FineTuneJobStatus.RUNNING, FineTuneJobStatus.PENDING].includes(
      tuna.status
    );
  }, [tuna.status]);

  const [canceling, setCanceling] = useState(false);

  const cancelJob = useCallback(() => {
    setCanceling(true);
    tunaService.cancelJob(tuna.id).subscribe({
      next: () => {
        refreshService.refresh();
        setCanceling(false);
      },
      error: () => {
        setCanceling(false);
      },
    });
  }, [tunaService, tuna.id, refreshService]);

  return (
    <Space
      wrap
      size={[0, 0]}
      align="end"
      css={css`
        justify-content: end;
        margin-top: 2px;
      `}
    >
      {deployed && (
        <>
          {inferenceEnabled && (
            <>
              <Button
                disabled={workspaceTrackerService.workspace?.isPastDue}
                size="small"
                key="try"
                type="text"
                icon={<CarbonIcon icon={<ChatBot />} />}
                onClick={gotoModelComparison}
              >
                Chat
              </Button>
              <ApiModal
                size="small"
                icon={<CarbonIcon icon={<Code />} />}
                name={tuna.name}
                apiUrl={inference?.status?.api_endpoint || ""}
                apiKey={workspaceTrackerService.workspace?.auth.token}
              >
                API
              </ApiModal>
            </>
          )}
          <Terminate name={tuna.name} />
        </>
      )}
      {!deployed && (
        <>
          <Button
            disabled={
              workspaceTrackerService.workspace?.isPastDue || !deployable
            }
            size="small"
            key="deploy"
            type="text"
            loading={deployLoading}
            icon={<CarbonIcon icon={<DeploymentIcon />} />}
            onClick={createDeployment}
          >
            Deploy
          </Button>
          {cancelable ? (
            <Popconfirm
              disabled={
                canceling || workspaceTrackerService.workspace?.isPastDue
              }
              title="Cancel this training job"
              description="Are you sure to cancel this training job?"
              onConfirm={cancelJob}
            >
              <Button
                disabled={workspaceTrackerService.workspace?.isPastDue}
                loading={canceling}
                size="small"
                key="cancel"
                type="text"
                icon={<CarbonIcon icon={<StopFilled />} />}
              >
                Cancel
              </Button>
            </Popconfirm>
          ) : null}
        </>
      )}
    </Space>
  );
};
