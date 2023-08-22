import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { TunaIcon } from "@lepton-dashboard/components/icons";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/deployment-status";
import { TunaStatus } from "../tuna-status";
import { Actions } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/tuna-item/actions";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Col, Row, Typography } from "antd";
import { FC, useState } from "react";
import { filter, switchMap, withLatestFrom } from "rxjs";

export const TunaItem: FC<{ tuna: FineTuneJob }> = ({ tuna }) => {
  const tunaService = useInject(TunaService);
  const refreshService = useInject(RefreshService);
  const [loading, setLoading] = useState(
    tuna.status === FineTuneJobStatus.SUCCESS
  );
  const status$ = useObservableFromState(tuna.status);
  const inference = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        withLatestFrom(status$),
        filter(([, status]) => status === FineTuneJobStatus.SUCCESS),
        switchMap(() => tunaService.getInference(tuna.name))
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
  return (
    <Card>
      <Row gutter={[16, 8]}>
        <Col span={24}>
          <div
            css={css`
              min-height: 50px;
            `}
          >
            <Row gutter={[16, 0]}>
              <Col span={24}>
                <Row justify="space-between" wrap={false}>
                  <Col flex="1 4 250px">
                    <Typography.Text strong>
                      <span
                        css={css`
                          font-size: 16px;
                          white-space: nowrap;
                        `}
                      >
                        <span
                          css={css`
                            margin-right: 8px;
                          `}
                        >
                          <TunaIcon />
                        </span>
                        <Typography.Text
                          css={css`
                            width: 80%;
                          `}
                          ellipsis={{ tooltip: true }}
                        >
                          {tuna.name}
                        </Typography.Text>
                      </span>
                    </Typography.Text>
                    <MinThemeProvider>
                      <div>
                        <Typography.Text type="secondary">
                          <DateParser prefix="Created" date={tuna.created_at} />
                        </Typography.Text>
                      </div>
                    </MinThemeProvider>
                  </Col>
                  <Col flex="0 1 auto">
                    {!loading && <Actions tuna={tuna} inference={inference} />}
                  </Col>
                </Row>
              </Col>
            </Row>
          </div>
        </Col>
        <Col span={24}>
          <Row gutter={[16, 8]}>
            <Col span={24}>
              <Row justify="space-between">
                <Col flex="0 0 auto">Training</Col>
                <Col flex="0 0 auto">
                  <TunaStatus status={tuna.status} />
                </Col>
              </Row>
            </Col>
            <Col span={24}>
              <Row justify="space-between">
                <Col flex="0 0 auto">Inference</Col>
                <Col flex="0 0 auto">
                  <DeploymentStatus
                    state={
                      inference?.status?.state ||
                      (loading ? "UNKNOWN" : "NOT DEPLOYED")
                    }
                  />
                </Col>
              </Row>
            </Col>
          </Row>
        </Col>
      </Row>
    </Card>
  );
};
