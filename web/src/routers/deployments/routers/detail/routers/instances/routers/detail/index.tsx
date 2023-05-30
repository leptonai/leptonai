import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  Navigate,
  Route,
  Routes,
  useParams,
  useResolvedPath,
} from "react-router-dom";
import { TerminalDetail } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/terminal";
import { LogDetail } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/logs-viewer";
import { MetricsDetail } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/metrics";
import { Container } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/routers/detail/components/container";
import { css } from "@emotion/react";

export const Detail: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const { id } = useParams();
  const { pathname } = useResolvedPath("");

  return (
    <Routes>
      <Route element={<Container instanceId={id!} deployment={deployment} />}>
        <Route
          path="terminal"
          element={
            <TerminalDetail deploymentId={deployment.id} instanceId={id!} />
          }
        />
        <Route
          path="logs"
          element={
            <div
              css={css`
                height: 500px;
              `}
            >
              <LogDetail deploymentId={deployment.id} instanceId={id!} />
            </div>
          }
        />
        <Route
          path="metrics"
          element={
            <MetricsDetail
              gpu={!!deployment.resource_requirement.accelerator_num}
              deploymentId={deployment.id}
              instanceId={id!}
            />
          }
        />
        <Route
          path="*"
          element={<Navigate to={`${pathname}/terminal`} replace />}
        />
      </Route>
    </Routes>
  );
};
