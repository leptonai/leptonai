import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { ProcessingWrapper } from "@lepton-dashboard/components/processing-wrapper";
import { State } from "@lepton-dashboard/interfaces/deployment";
import { SmallTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/small-tag";
import { FC, useMemo } from "react";

export const DeploymentStatus: FC<{ state?: string }> = ({ state }) => {
  const color = useMemo(() => {
    switch (state) {
      case State.Running:
        return "success";
      case State.NotReady:
        return "warning";
      case State.Starting:
        return "processing";
      default:
        return "default";
    }
  }, [state]);
  return (
    <ProcessingWrapper processing={state?.toUpperCase() === "STARTING"}>
      <SmallTag icon={<DeploymentIcon />} color={color}>
        {state?.toUpperCase() || "UNKNOWN"}
      </SmallTag>
    </ProcessingWrapper>
  );
};
