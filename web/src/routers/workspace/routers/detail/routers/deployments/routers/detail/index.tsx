import { Card } from "@lepton-dashboard/components/card";
import { Metrics } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/metrics";
import { Empty } from "antd";
import { FC } from "react";
import { Route, Routes, useParams } from "react-router-dom";
import { Container } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/container";
import { Demo } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Api } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api";
import { List as ReplicaList } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/routers/list";
import { Detail as ReplicaDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/routers/detail";
import { Events } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/events";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Detail: FC = () => {
  const { id } = useParams();
  const deploymentService = useInject(DeploymentService);
  const deployment = useStateFromObservable(
    () => deploymentService.id(id!),
    undefined
  );
  return deployment ? (
    <Routes>
      <Route element={<Container deployment={deployment} />}>
        <Route path="demo" element={<Demo deployment={deployment} />} />
        <Route path="api" element={<Api deployment={deployment} />} />
        <Route path="events" element={<Events deployment={deployment} />} />
        <Route path="metrics" element={<Metrics deployment={deployment} />} />
        <Route
          path="replicas/list"
          element={<ReplicaList deployment={deployment} />}
        />
      </Route>
      <Route
        path="replicas/detail/:id/*"
        element={<ReplicaDetail deployment={deployment} />}
      />
      <Route
        path="*"
        element={
          <NavigateTo
            name="deploymentDetailDemo"
            params={{
              deploymentId: id!,
            }}
            replace
          />
        }
      />
    </Routes>
  ) : (
    <Card>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="Deployment Not Found"
      />
    </Card>
  );
};
