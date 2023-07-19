import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { useInject } from "@lepton-libs/di";
import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Route, Routes, useParams } from "react-router-dom";
import { TerminalDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/terminal";
import { LogDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/logs-viewer";
import { MetricsDetail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/metrics";
import { Container } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/routers/detail/components/container";
import { css } from "@emotion/react";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Detail: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const { id } = useParams();
  const hardwareService = useInject(HardwareService);
  return (
    <Routes>
      <Route element={<Container replicaId={id!} deployment={deployment} />}>
        <Route
          path="terminal"
          element={
            <TerminalDetail deploymentName={deployment.name} replicaId={id!} />
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
              <LogDetail deploymentName={deployment.name} replicaId={id!} />
            </div>
          }
        />
        <Route
          path="metrics"
          element={
            <MetricsDetail
              gpu={hardwareService.isGPUInstance(
                deployment.resource_requirement.resource_shape
              )}
              deploymentName={deployment.name}
              replicaId={id!}
            />
          }
        />
        <Route
          path="*"
          element={
            <NavigateTo
              name="deploymentDetailReplicasTerminal"
              params={{
                deploymentName: deployment.name,
                replicaId: id!,
              }}
              replace
            />
          }
        />
      </Route>
    </Routes>
  );
};
