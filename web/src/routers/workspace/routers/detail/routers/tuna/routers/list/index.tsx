import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, useMemo, useState } from "react";
import { Col, Row, Button, Empty, Spin, Modal, Select, Input } from "antd";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";

import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { switchMap } from "rxjs";
import { Card } from "@lepton-dashboard/components/card";
import { JobItem } from "../../components/item";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { CreateJob } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/create";

export const List: FC = () => {
  const refreshService = useInject(RefreshService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const fineTuneService = useInject(TunaService);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [search, setSearch] = useState<string>("");
  const [status, setStatus] = useState<string[]>([]);
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
  const filteredModels = useMemo(() => {
    return models.filter(
      (d) =>
        (status.length === 0 || status.indexOf(d.status) !== -1) &&
        JSON.stringify(d).indexOf(search) !== -1
    );
  }, [models, search, status]);

  const closeCreateModal = () => {
    setCreateModalOpen(false);
  };

  return (
    <>
      <Row gutter={[8, 24]}>
        <Col span={24}>
          <Row gutter={[8, 8]} justify="space-between">
            <Col flex="1 1 300px">
              <Input
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                prefix={<SearchOutlined />}
                placeholder="Search"
              />
            </Col>
            <Col flex="0 1 300px">
              <Select
                style={{ width: "100%" }}
                mode="multiple"
                value={status}
                placeholder="Tuna status"
                onChange={(v) => setStatus(v)}
                maxTagCount={1}
                options={[
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
                ]}
              />
            </Col>
            <Col flex="0 0 auto">
              <Button
                type="primary"
                disabled={workspaceTrackerService.workspace?.isPastDue}
                icon={<PlusOutlined />}
                onClick={() => setCreateModalOpen(true)}
              >
                Create tuna
              </Button>
            </Col>
          </Row>
        </Col>
        <Col span={24}>
          <Spin spinning={loading}>
            {filteredModels.length > 0 ? (
              <Row gutter={[16, 16]} wrap>
                {filteredModels.map((model) => (
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
                  description="No tuna found"
                />
              </Card>
            )}
          </Spin>
        </Col>
      </Row>
      <Modal
        destroyOnClose
        title="Create tuna"
        open={createModalOpen}
        onCancel={closeCreateModal}
        footer={null}
      >
        <CreateJob finish={closeCreateModal} />
      </Modal>
    </>
  );
};
