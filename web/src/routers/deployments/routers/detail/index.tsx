import { FC } from "react";
import {
  Navigate,
  Route,
  Routes,
  useParams,
  useResolvedPath,
} from "react-router-dom";
import { Container } from "@lepton-dashboard/routers/deployments/routers/detail/components/container";
import { Demo } from "@lepton-dashboard/routers/deployments/routers/detail/routers/demo";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Api } from "@lepton-dashboard/routers/deployments/routers/detail/routers/api";
import { Instances } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances";

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
        <Route path="demo" element={<Demo />} />
        <Route path="api" element={<Api />} />
        <Route path="instances" element={<Instances />} />
        <Route
          path="*"
          element={<Navigate to={`${pathname}/demo`} replace />}
        />
      </Route>
    </Routes>
  ) : (
    <></>
  );
};
