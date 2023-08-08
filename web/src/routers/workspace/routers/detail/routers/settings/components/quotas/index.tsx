import { Quota } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/components/quota";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Col, Row } from "antd";
import { FC } from "react";

export const Quotas: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const resource_quota =
    workspaceTrackerService.workspace?.data?.resource_quota;
  return resource_quota ? (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Quota
          used={resource_quota?.used.cpu}
          limit={resource_quota?.limit.cpu}
          name="CPU"
          unit=""
        />
      </Col>

      <Col span={24}>
        <Quota
          used={resource_quota?.used.accelerator_num}
          limit={resource_quota?.limit.accelerator_num}
          name="GPU"
          unit="card"
        />
      </Col>
      <Col span={24}>
        <Quota
          used={resource_quota?.used.memory}
          limit={resource_quota?.limit.memory}
          name="Memory"
          unit="MiB"
        />
      </Col>
    </Row>
  ) : (
    <></>
  );
};
