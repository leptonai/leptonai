import { AntdRoot } from "@lepton-dashboard/components/antd-root";
import { lazyErrorWrapper } from "@lepton-dashboard/components/lazy-error-wrapper";
import { AuthTokenService } from "@lepton-dashboard/services/auth.token.service";
import { AuthPortalService } from "@lepton-dashboard/services/auth-portal.service";
import { TrackerService } from "@lepton-dashboard/services/tracker.service";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { OpenApiService } from "@lepton-dashboard/services/open-api.service";
import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { MetaService } from "@lepton-dashboard/services/meta.service";
import { InitializerService } from "@lepton-dashboard/services/initializer.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { Root } from "@lepton-dashboard/components/root";
import {
  AxiosHandler,
  HttpClientService,
  HTTPInterceptorToken,
} from "@lepton-dashboard/services/http-client.service";
import { lazy } from "react";
import { StorageService } from "@lepton-dashboard/services/storage.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import {
  IdentificationGuard,
  OAuthGuard,
  WorkspaceGuard,
} from "./components/auth-guard";
import { AppInterceptor } from "@lepton-dashboard/interceptors/app.interceptor";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import "./log";

const Login = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/login").then((e) => ({
      default: e.Login,
    }))
  )
);
const Credentials = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/credentials").then((e) => ({
      default: e.Credentials,
    }))
  )
);
const CloseBeta = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/close-beta").then((e) => ({
      default: e.CloseBeta,
    }))
  )
);
const WaitList = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/wait-list").then((e) => ({
      default: e.WaitList,
    }))
  )
);
const NoWorkspace = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/no-workspace").then((e) => ({
      default: e.NoWorkspace,
    }))
  )
);
const Workspace = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/workspace").then((e) => ({
      default: e.Workspace,
    }))
  )
);
const Playground = lazyErrorWrapper(
  lazy(() =>
    import("@lepton-dashboard/routers/playground").then((e) => ({
      default: e.Playground,
    }))
  )
);

const router = createBrowserRouter([
  {
    path: "playground/*",
    element: (
      <AntdRoot>
        <Playground />
      </AntdRoot>
    ),
  },
  {
    path: "*",
    element: (
      <AntdRoot>
        <Root />
      </AntdRoot>
    ),
    children: [
      {
        path: "login",
        element: <Login />,
      },
      {
        path: "credentials",
        element: (
          <OAuthGuard>
            <Credentials />
          </OAuthGuard>
        ),
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
        path: "waitlist",
        element: (
          <OAuthGuard>
            <WaitList />
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
        MetaService,
        InitializerService,
        RefreshService,
        AxiosHandler,
        HttpClientService,
        StorageService,
        OpenApiService,
        ProfileService,
        AuthTokenService,
        AuthPortalService,
        NavigateService,
        WorkspaceTrackerService,
        NotificationService,
        HardwareService,
        TrackerService,
        {
          provide: HTTPInterceptorToken,
          useClass: AppInterceptor,
        },
        {
          provide: AuthService,
          useFactory: (
            authPortalService: AuthPortalService,
            authNoopService: AuthTokenService
          ) => {
            if (import.meta.env.VITE_ENABLE_OAUTH === "enable") {
              return authPortalService;
            } else {
              return authNoopService;
            }
          },
          deps: [AuthPortalService, AuthTokenService],
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
