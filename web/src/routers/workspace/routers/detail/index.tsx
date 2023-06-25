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
import {
  FullLayoutWidth,
  Layout,
  LimitedLayoutWidth,
} from "../../../../components/layout";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { Nav } from "@lepton-dashboard/routers/workspace/components/nav";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";
import { Header } from "@lepton-dashboard/components/layout/components/header";
import { WorkspaceSwitch } from "@lepton-dashboard/routers/workspace/components/workspace-switch";
import { ProfileMenu } from "@lepton-dashboard/routers/workspace/components/profile-menu";
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

const Secrets = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/secrets"
  ).then((e) => ({
    default: e.Secrets,
  }))
);

const Settings = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/settings"
  ).then((e) => ({
    default: e.Settings,
  }))
);

const FineTune = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/fine-tune"
  ).then((e) => ({
    default: e.FineTune,
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
    <Layout
      nav={<Nav />}
      footer={<Footer />}
      header={<Header menu={<WorkspaceSwitch />} actions={<ProfileMenu />} />}
    >
      <Suspense
        fallback={
          <LimitedLayoutWidth>
            <Loading />
          </LimitedLayoutWidth>
        }
      >
        <Routes>
          <Route
            path="dashboard"
            element={
              <LimitedLayoutWidth>
                <Dashboard />
              </LimitedLayoutWidth>
            }
          />
          <Route
            path="photons/*"
            element={
              <LimitedLayoutWidth>
                <Photons />
              </LimitedLayoutWidth>
            }
          />
          <Route
            path="deployments/*"
            element={
              <LimitedLayoutWidth>
                <Deployments />
              </LimitedLayoutWidth>
            }
          />
          <Route
            path="secrets"
            element={
              <LimitedLayoutWidth>
                <Secrets />
              </LimitedLayoutWidth>
            }
          />
          <Route
            path="settings/*"
            element={
              <FullLayoutWidth>
                <Settings />
              </FullLayoutWidth>
            }
          />
          <Route
            path="fine-tune/*"
            element={
              <LimitedLayoutWidth>
                <FineTune />
              </LimitedLayoutWidth>
            }
          />
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
