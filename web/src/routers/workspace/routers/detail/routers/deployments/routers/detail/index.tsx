import { FC } from "react";
import {
  Navigate,
  Route,
  Routes,
  useParams,
  useResolvedPath,
} from "react-router-dom";
import { Container } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/container";
import { Demo } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/demo";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Api } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/api";
import { List as InstanceList } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/routers/list";
import { Detail as InstanceDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/routers/detail";

export const Detail: FC = () => {
  const { id } = useParams();
  const deploymentService = useInject(DeploymentService);
  const deployment = useStateFromObservable(
    () => deploymentService.id(id!),
    undefined
  );
  const { pathname } = useResolvedPath("");
  return deployment ? (
    <Routes>
      <Route element={<Container deployment={deployment} />}>
        <Route path="demo" element={<Demo deployment={deployment} />} />
        <Route path="api" element={<Api deployment={deployment} />} />
        <Route
          path="instances/list"
          element={<InstanceList deployment={deployment} />}
        />
      </Route>
      <Route
        path="instances/detail/:id/*"
        element={<InstanceDetail deployment={deployment} />}
      />
      <Route path="*" element={<Navigate to={`${pathname}/demo`} replace />} />
    </Routes>
  ) : (
    <></>
  );
};
