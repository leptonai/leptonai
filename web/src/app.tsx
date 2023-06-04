import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Layout } from "@lepton-dashboard/components/layout";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { ApiService } from "@lepton-dashboard/services/api.service";
import { InitializerService } from "@lepton-dashboard/services/initializer.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { Root } from "@lepton-dashboard/components/root";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";
import { App as AntdApp } from "antd";
import { css } from "@emotion/react";
import { ApiServerService } from "@lepton-dashboard/services/api.server.service";
import { lazy } from "react";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { StorageService } from "@lepton-dashboard/services/storage.service";
import { JsonSchemaService } from "@lepton-dashboard/services/json-schema.service";
import { Login } from "@lepton-dashboard/routers/login";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { ClusterService } from "@lepton-dashboard/services/cluster.service";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
const Dashboard = lazy(() =>
  import("@lepton-dashboard/routers/dashboard").then((e) => ({
    default: e.Dashboard,
  }))
);

const Photons = lazy(() =>
  import("@lepton-dashboard/routers/photons").then((e) => ({
    default: e.Photons,
  }))
);

const Deployments = lazy(() =>
  import("@lepton-dashboard/routers/deployments").then((e) => ({
    default: e.Deployments,
  }))
);

const router = createBrowserRouter([
  {
    path: "login",
    element: <Login />,
  },
  {
    path: "*",
    element: (
      <AntdApp
        notification={{ maxCount: 1 }}
        css={css`
          height: 100%;
        `}
      >
        <Root>
          <Layout />
        </Root>
      </AntdApp>
    ),
    children: [
      {
        path: "dashboard",
        element: <Dashboard />,
      },
      {
        path: "photons/*",
        element: <Photons />,
      },
      {
        path: "deployments/*",
        element: <Deployments />,
      },
      {
        path: "*",
        element: <Navigate to="dashboard" replace />,
      },
    ],
  },
]);

function App() {
  return (
    <DIContainer
      providers={[
        ThemeService,
        TitleService,
        AuthService,
        ClusterService,
        PhotonService,
        DeploymentService,
        InitializerService,
        RefreshService,
        HttpClientService,
        NotificationService,
        StorageService,
        JsonSchemaService,
        OpenApiService,
        { provide: ApiService, useClass: ApiServerService },
      ]}
    >
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </DIContainer>
  );
}

export default App;
