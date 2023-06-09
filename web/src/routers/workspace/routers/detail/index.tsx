import { FC, Suspense, lazy } from "react";
import {
  Navigate,
  Route,
  Routes,
  useParams,
  useResolvedPath,
} from "react-router-dom";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { forkJoin, map, merge, switchMap } from "rxjs";
import { Loading } from "@lepton-dashboard/components/loading";
import { Layout } from "../../components/layout";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
const Dashboard = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/dashboard"
  ).then((e) => ({
    default: e.Dashboard,
  }))
);

const Photons = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/photons"
  ).then((e) => ({
    default: e.Photons,
  }))
);

const Deployments = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments"
  ).then((e) => ({
    default: e.Deployments,
  }))
);
export const Detail: FC = () => {
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const photonService = useInject(PhotonService);
  const { pathname } = useResolvedPath("");
  const { workspaceName } = useParams();
  const workspaceName$ = useObservableFromState(workspaceName);

  const initialized = useStateFromObservable(
    () =>
      merge(
        refreshService.refresh$.pipe(
          switchMap(() => {
            return forkJoin([
              deploymentService.refresh(),
              photonService.refresh(),
            ]);
          }),
          map(() => true)
        ),
        workspaceName$.pipe(map(() => false))
      ),
    false
  );
  return initialized ? (
    <Layout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="photons/*" element={<Photons />} />
          <Route path="deployments/*" element={<Deployments />} />
          <Route
            path="*"
            element={<Navigate to={`${pathname}/dashboard`} replace />}
          />
        </Routes>
      </Suspense>
    </Layout>
  ) : (
    <Loading />
  );
};
