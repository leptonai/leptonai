import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Models } from "@lepton-dashboard/routers/models";
import { Deployments } from "@lepton-dashboard/routers/deployments";
import { Layout } from "@lepton-dashboard/components/layout";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { Dashboard } from "@lepton-dashboard/routers/dashboard";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";
import { Root } from "@lepton-dashboard/components/root";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";

const router = createBrowserRouter([
  {
    path: "*",
    element: <Layout />,
    children: [
      {
        path: "dashboard",
        element: <Dashboard />,
      },
      {
        path: "models/*",
        element: <Models />,
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
      providers={[ThemeService, TitleService, ModelService, DeploymentService]}
    >
      <ThemeProvider>
        <Root>
          <RouterProvider router={router} />
        </Root>
      </ThemeProvider>
    </DIContainer>
  );
}

export default App;
