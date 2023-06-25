import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { FC, Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Loading } from "@lepton-dashboard/components/loading";
import { Validate } from "./components/validate";
import { DIContainer } from "@lepton-libs/di";
import { WorkspaceTrackerService } from "./services/workspace-tracker.service";
import { PhotonService } from "./services/photon.service";
import { DeploymentService } from "./services/deployment.service";
import { ApiService } from "./services/api.service";
import { ApiServerService } from "./services/api.server.service";
import { IndicatorService } from "./services/indicator.service";
import { FineTuneService } from "@lepton-dashboard/routers/workspace/services/fine-tune.service";

const Detail = lazy(() =>
  import("@lepton-dashboard/routers/workspace/routers/detail").then((e) => ({
    default: e.Detail,
  }))
);

export const Workspace: FC = () => {
  return (
    <DIContainer
      providers={[
        WorkspaceTrackerService,
        IndicatorService,
        PhotonService,
        MetricUtilService,
        DeploymentService,
        SecretService,
        FineTuneService,
        { provide: ApiService, useClass: ApiServerService },
      ]}
    >
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route
            path=":workspaceName/*"
            element={
              <Validate>
                <Detail />
              </Validate>
            }
          />
          <Route path="*" element={<Validate />} />
        </Routes>
      </Suspense>
    </DIContainer>
  );
};
