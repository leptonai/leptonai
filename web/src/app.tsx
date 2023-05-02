import { DIContainer } from "@lepton-libs/di";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Overview } from "@lepton-dashboard/routers/overview";
import { Models } from "@lepton-dashboard/routers/models";
import { Deployments } from "@lepton-dashboard/routers/deployments";
import { Layout } from "@lepton-dashboard/components/layout";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";

const router = createBrowserRouter([
  {
    path: "*",
    element: <Layout />,
    children: [
      {
        path: "overview",
        element: <Overview />,
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
        element: <Navigate to="overview" />,
      },
    ],
  },
]);

function App() {
  return (
    <DIContainer providers={[ThemeService]}>
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </DIContainer>
  );
}

export default App;
