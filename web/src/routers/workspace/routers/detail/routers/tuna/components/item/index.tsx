import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, ReactNode, useCallback, useMemo, useState } from "react";
import { Button, Col, Popconfirm, Row, Space, Tag } from "antd";
import { CarbonIcon, DeploymentIcon } from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { Code, PlayFilledAlt, StopFilled, Time } from "@carbon/icons-react";
import { useInject } from "@lepton-libs/di";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { StatusTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/status-tag";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { filter, switchMap, withLatestFrom } from "rxjs";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { ApiModal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/api-modal";

const SmallTag = ({
  children,
  color,
}: {
  children: ReactNode;
  color?: string;
}) => {
  const theme = useAntdTheme();
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
        colorBorderSecondary: "transparent",
      }}
    >
      <Tag
        color={color}
        css={css`
          margin-right: 0;
          color: ${theme.colorText};
        `}
      >
        {children}
      </Tag>
    </ThemeProvider>
  );
};

export const JobItem: FC<{
  job: FineTuneJob;
}> = ({ job }) => {
  const fineTuneService = useInject(TunaService);
  const refreshService = useInject(RefreshService);
  const navigateService = useInject(NavigateService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const [loading, setLoading] = useState(
    job.status === FineTuneJobStatus.SUCCESS
  );
  const [canceling, setCanceling] = useState(false);
  const status$ = useObservableFromState(job.status);

  const inference = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        withLatestFrom(status$),
        filter(([, status]) => status === FineTuneJobStatus.SUCCESS),
        switchMap(() => fineTuneService.getInference(job.name))
      ),
    null,
    {
      next: () => {
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  const deployed = useMemo(() => {
    return !loading && inference !== null;
  }, [inference, loading]);

  const deployable = useMemo(() => {
    return (
      [FineTuneJobStatus.SUCCESS].includes(job.status) && !deployed && !loading
    );
  }, [job.status, deployed, loading]);

  const cancelable = useMemo(() => {
    return [FineTuneJobStatus.RUNNING, FineTuneJobStatus.PENDING].includes(
      job.status
    );
  }, [job.status]);

  const cancelJob = useCallback(() => {
    setCanceling(true);
    fineTuneService.cancelJob(job.id).subscribe({
      next: () => {
        refreshService.refresh();
        setCanceling(false);
      },
      error: () => {
        setCanceling(false);
      },
    });
  }, [fineTuneService, job.id, refreshService]);

  const createDeployment = useCallback(() => {
    fineTuneService.createInference(job.name, job.output_dir).subscribe({
      next: () => {
        refreshService.refresh();
      },
    });
  }, [fineTuneService, job.name, job.output_dir, refreshService]);

  const gotoModelComparison = useCallback(() => {
    if (!inference?.metadata.name) {
      return;
    }
    navigateService.navigateTo("tunaChat", {
      inferenceName: inference.metadata.name,
    });
  }, [navigateService, inference]);
  return (
    <>
      <Row gutter={[0, 12]}>
        <Col span={24}>
          <Row gutter={[0, 12]}>
            <Col flex="1 1 auto">
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                term={
                  <>
                    <StatusTag status={job.status} /> {job.name || "-"}
                  </>
                }
              />
            </Col>
            <Col
              flex="0 0 auto"
              css={css`
                position: relative;
                left: -6px;
              `}
            >
              <Space wrap size={[12, 4]}>
                {deployed && (
                  <>
                    <ApiModal
                      disabled={!deployed}
                      icon={<CarbonIcon icon={<Code />} />}
                      apiUrl={inference?.status?.api_endpoint || ""}
                      name={job.name}
                    >
                      API
                    </ApiModal>
                    <Button
                      disabled={!deployed}
                      size="small"
                      key="try"
                      type="text"
                      icon={<CarbonIcon icon={<PlayFilledAlt />} />}
                      onClick={gotoModelComparison}
                    >
                      Try it out
                    </Button>
                  </>
                )}
                {!deployed && (
                  <>
                    <Button
                      disabled={
                        workspaceTrackerService.workspace?.isPastDue ||
                        !deployable
                      }
                      size="small"
                      key="deploy"
                      type="text"
                      icon={<CarbonIcon icon={<DeploymentIcon />} />}
                      onClick={createDeployment}
                    >
                      Deploy
                    </Button>
                    <Popconfirm
                      disabled={
                        !cancelable ||
                        canceling ||
                        workspaceTrackerService.workspace?.isPastDue
                      }
                      title="Cancel this training job"
                      description="Are you sure to cancel this training job?"
                      onConfirm={cancelJob}
                    >
                      <Button
                        disabled={
                          !cancelable ||
                          workspaceTrackerService.workspace?.isPastDue
                        }
                        loading={canceling}
                        size="small"
                        key="cancel"
                        type="text"
                        icon={<CarbonIcon icon={<StopFilled />} />}
                      >
                        Cancel
                      </Button>
                    </Popconfirm>
                  </>
                )}
              </Space>
            </Col>
          </Row>
        </Col>
        <Col span={24}>
          <Row>
            <Col flex="1 1 auto">
              <Description.Container
                css={css`
                  font-size: 12px;
                `}
              >
                <SmallTag color={deployed ? "success" : ""}>
                  <Description.Item
                    icon={<DeploymentIcon />}
                    description={deployed ? "Deployed" : "Not Deployed"}
                  />
                </SmallTag>
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <DateParser
                      detail
                      prefix="Created at"
                      date={job.created_at}
                    />
                  }
                />
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <DateParser
                      detail
                      prefix="Modified at"
                      date={job.modified_at}
                    />
                  }
                />
              </Description.Container>
            </Col>
          </Row>
        </Col>
      </Row>
    </>
  );
};
