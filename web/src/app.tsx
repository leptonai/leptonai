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
        path: "models",
        element: <Models />,
      },
      {
        path: "deployments",
        element: <Deployments />,
      },
      {
        path: "*",
        element: <Navigate to="dashboard" />,
      },
    ],
  },
]);

function App() {
  return (
    <DIContainer providers={[ThemeService]}>
      <ThemeProvider>
        <Root>
          <RouterProvider router={router} />
        </Root>
      </ThemeProvider>
    </DIContainer>
  );
}

export default App;
