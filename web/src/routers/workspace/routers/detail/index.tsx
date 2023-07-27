import { Card } from "@lepton-dashboard/components/card";
import { GettingStarted } from "@lepton-dashboard/routers/workspace/components/getting-started";
import { Dashboard } from "@lepton-dashboard/routers/workspace/routers/detail/routers/dashboard";
import { Deployments } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments";
import { Photons } from "@lepton-dashboard/routers/workspace/routers/detail/routers/photons";
import { Settings } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings";
import { Storage } from "@lepton-dashboard/routers/workspace/routers/detail/routers/storage";
import { Button, Result, Typography } from "antd";
import { FC, Suspense, lazy } from "react";
import { Route, Routes, useParams } from "react-router-dom";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { catchError, forkJoin, map, merge, of, switchMap } from "rxjs";
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
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

const FineTune = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna"
  ).then((e) => ({
    default: e.Tuna,
  }))
);

export const Detail: FC = () => {
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const photonService = useInject(PhotonService);
  const { workspaceId } = useParams();
  const workspaceId$ = useObservableFromState(workspaceId);

  const state = useStateFromObservable(
    () =>
      merge(
        refreshService.refresh$.pipe(
          switchMap(() => {
            return forkJoin([
              deploymentService.refresh(),
              photonService.refresh(),
            ]);
          }),
          map(() => "normal"),
          catchError(() => of("error"))
        ),
        workspaceId$.pipe(map(() => "initializing"))
      ),
    "initializing"
  );
  if (state === "initializing") {
    return <Loading />;
  } else {
    return (
      <Layout
        nav={<Nav />}
        footer={<Footer />}
        header={<Header menu={<WorkspaceSwitch />} actions={<ProfileMenu />} />}
      >
        {state === "normal" ? (
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
                path="getting-started"
                element={
                  <LimitedLayoutWidth>
                    <GettingStarted />
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
                path="storage"
                element={
                  <LimitedLayoutWidth>
                    <Storage />
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
                path="tuna/*"
                element={
                  <LimitedLayoutWidth>
                    <FineTune />
                  </LimitedLayoutWidth>
                }
              />
              <Route
                path="*"
                element={<NavigateTo name="dashboard" replace />}
              />
            </Routes>
          </Suspense>
        ) : (
          <LimitedLayoutWidth>
            <Card>
              <Result
                title="Temporarily unavailable"
                subTitle={
                  <Typography.Text>
                    Workspace{" "}
                    <Typography.Text code>{workspaceId}</Typography.Text> is
                    temporarily unavailable, stay tuned.
                  </Typography.Text>
                }
                extra={
                  <Button type="primary" onClick={() => location.reload()}>
                    Try again
                  </Button>
                }
              />
            </Card>
          </LimitedLayoutWidth>
        )}
      </Layout>
    );
  }
};
