import { Detail } from "@lepton-dashboard/routers/workspace/routers/detail";
import { BillingService } from "@lepton-dashboard/routers/workspace/services/billing.service";
import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { WorkspaceService } from "@lepton-dashboard/routers/workspace/services/workspace.service";
import { FC, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Loading } from "@lepton-dashboard/components/loading";
import { Validate } from "./components/validate";
import { DIContainer } from "@lepton-libs/di";
import { PhotonService } from "./services/photon.service";
import { DeploymentService } from "./services/deployment.service";
import { ApiService } from "./services/api.service";
import { ApiServerService } from "./services/api.server.service";
import { IndicatorService } from "./services/indicator.service";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { FileManagerServerService } from "@lepton-dashboard/routers/workspace/services/file-manager-server.service";
import { FileManagerService } from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { ImagePullSecretService } from "@lepton-dashboard/routers/workspace/services/image-pull-secret.service";

export const Workspace: FC = () => {
  return (
    <DIContainer
      providers={[
        IndicatorService,
        PhotonService,
        WorkspaceService,
        MetricUtilService,
        DeploymentService,
        SecretService,
        TunaService,
        BillingService,
        ImagePullSecretService,
        { provide: ApiService, useClass: ApiServerService },
        { provide: FileManagerService, useClass: FileManagerServerService },
      ]}
    >
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route
            path=":workspaceId/*"
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
