import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Layout } from "@lepton-dashboard/components/layout";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";
import { InitializerService } from "@lepton-dashboard/services/initializer.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { Root } from "@lepton-dashboard/components/root";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service.ts";
import { App as AntdApp } from "antd";
import { css } from "@emotion/react";
import { ApiServerService } from "@lepton-dashboard/services/api.server.service.ts";
import { lazy } from "react";
import { NotificationService } from "@lepton-dashboard/services/notification.service.ts";
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
        PhotonService,
        DeploymentService,
        InitializerService,
        RefreshService,
        HttpClientService,
        NotificationService,
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
