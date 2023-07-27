import { css } from "@emotion/react";
import { FC, useMemo, useState } from "react";
import { Col, Row, Radio, Button, Empty, Spin, Modal } from "antd";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";

import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { switchMap } from "rxjs";
import { Card } from "@lepton-dashboard/components/card";
import { JobItem } from "../../components/item";
import { PlusOutlined } from "@ant-design/icons";
import { CreateJob } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/create";

const AllStatus = "#all";

const FilterConfig = {
  status: [
    {
      value: AllStatus,
      label: "All",
    },
    {
      value: FineTuneJobStatus.SUCCESS,
      label: "SUCCESS",
    },
    {
      value: FineTuneJobStatus.RUNNING,
      label: "RUNNING",
    },
    {
      value: FineTuneJobStatus.PENDING,
      label: "PENDING",
    },
    {
      value: FineTuneJobStatus.CANCELLED,
      label: "CANCELLED",
    },
    {
      value: FineTuneJobStatus.FAILED,
      label: "FAILED",
    },
  ],
};

export const List: FC = () => {
  const refreshService = useInject(RefreshService);
  const fineTuneService = useInject(TunaService);
  const [status, setStatus] = useState<string>(AllStatus);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const models = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(switchMap(() => fineTuneService.listJobs())),
    [],
    {
      next: () => {
        setLoading(false);
      },
    }
  );

  const filteredFineTunes = useMemo(() => {
    if (status === AllStatus) {
      return models;
    }
    return models.filter((e) => e.status === status);
  }, [models, status]);

  const statusCount = useMemo(() => {
    return models.reduce(
      (acc, cur) => {
        acc[cur.status] = acc[cur.status] || 0;
        acc[cur.status]++;
        return acc;
      },
      {
        [AllStatus]: models.length,
      } as Record<FineTuneJobStatus | typeof AllStatus, number>
    );
  }, [models]);

  const closeCreateModal = () => {
    setCreateModalOpen(false);
  };

  return (
    <>
      <Row gutter={[8, 24]}>
        <Col span={24}>
          <Row gutter={[8, 8]} justify="space-between">
            <Col flex={1}>
              <Radio.Group
                buttonStyle="solid"
                value={status}
                css={css`
                  display: flex;
                  max-width: 100%;
                `}
                onChange={(e) => setStatus(e.target.value)}
              >
                {FilterConfig.status.map((e) => (
                  <Radio.Button
                    css={css`
                      text-overflow: ellipsis;
                      overflow: hidden;
                    `}
                    key={e.value}
                    value={e.value}
                  >
                    {e.label}&nbsp;(
                    {statusCount[e.value as FineTuneJobStatus] || 0})
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalOpen(true)}
              >
                New Model
              </Button>
            </Col>
          </Row>
        </Col>
        <Col span={24}>
          <Spin spinning={loading} tip="loading…">
            {filteredFineTunes.length > 0 ? (
              <Row gutter={[16, 16]} wrap>
                {filteredFineTunes.map((model) => (
                  <Col span={24} key={`${model.id}`}>
                    <Card className="photon-item">
                      <JobItem job={model} />
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : (
              <Card>
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="No Models"
                />
              </Card>
            )}
          </Spin>
        </Col>
      </Row>
      <Modal
        destroyOnClose
        title="Create Model"
        open={createModalOpen}
        onCancel={closeCreateModal}
        footer={null}
      >
        <CreateJob finish={closeCreateModal} />
      </Modal>
    </>
  );
};
