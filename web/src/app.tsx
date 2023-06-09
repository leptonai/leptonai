import { AuthNoopService } from "@lepton-dashboard/services/auth.noop.service";
import { AuthSupabaseService } from "@lepton-dashboard/services/auth.supabase.service";
import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { InitializerService } from "@lepton-dashboard/services/initializer.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { Root } from "@lepton-dashboard/components/root";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";
import { App as AntdApp } from "antd";
import { css } from "@emotion/react";
import { lazy } from "react";
import { StorageService } from "@lepton-dashboard/services/storage.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import {
  IdentificationGuard,
  OAuthGuard,
  WorkspaceGuard,
} from "./components/auth-guard";

const Login = lazy(() =>
  import("@lepton-dashboard/routers/login").then((e) => ({
    default: e.Login,
  }))
);
const CloseBeta = lazy(() =>
  import("@lepton-dashboard/routers/close-beta").then((e) => ({
    default: e.CloseBeta,
  }))
);
const NoWorkspace = lazy(() =>
  import("@lepton-dashboard/routers/no-workspace").then((e) => ({
    default: e.NoWorkspace,
  }))
);
const Workspace = lazy(() =>
  import("@lepton-dashboard/routers/workspace").then((e) => ({
    default: e.Workspace,
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
        <Root />
      </AntdApp>
    ),
    children: [
      {
        path: "login",
        element: <Login />,
      },
      {
        path: "closebeta",
        element: (
          <OAuthGuard>
            <CloseBeta />
          </OAuthGuard>
        ),
      },
      {
        path: "no-workspace",
        element: (
          <OAuthGuard>
            <IdentificationGuard>
              <NoWorkspace />
            </IdentificationGuard>
          </OAuthGuard>
        ),
      },
      {
        path: "workspace/*",
        element: (
          <OAuthGuard>
            <IdentificationGuard>
              <WorkspaceGuard>
                <Workspace />
              </WorkspaceGuard>
            </IdentificationGuard>
          </OAuthGuard>
        ),
      },
      {
        path: "*",
        element: <Navigate to="/workspace" replace />,
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
        InitializerService,
        RefreshService,
        HttpClientService,
        StorageService,
        ProfileService,
        AuthNoopService,
        AuthSupabaseService,
        {
          provide: AuthService,
          useFactory: (
            authSupabaseService: AuthSupabaseService,
            authNoopService: AuthNoopService
          ) => {
            if (import.meta.env.VITE_ENABLE_OAUTH === "enable") {
              return authSupabaseService;
            } else {
              return authNoopService;
            }
          },
          deps: [AuthSupabaseService, AuthNoopService],
        },
      ]}
    >
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </DIContainer>
  );
}

export default App;
