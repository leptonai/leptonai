import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  Navigate,
  Route,
  Routes,
  useParams,
  useResolvedPath,
} from "react-router-dom";
import { TerminalDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/terminal";
import { LogDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/logs-viewer";
import { MetricsDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/metrics";
import { Container } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/routers/detail/components/container";
import { css } from "@emotion/react";

export const Detail: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const { id } = useParams();
  const { pathname } = useResolvedPath("");

  return (
    <Routes>
      <Route element={<Container replicaId={id!} deployment={deployment} />}>
        <Route
          path="terminal"
          element={
            <TerminalDetail deploymentId={deployment.id} replicaId={id!} />
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
              <LogDetail deploymentId={deployment.id} replicaId={id!} />
            </div>
          }
        />
        <Route
          path="metrics"
          element={
            <MetricsDetail
              gpu={!!deployment.resource_requirement.accelerator_num}
              deploymentId={deployment.id}
              replicaId={id!}
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
