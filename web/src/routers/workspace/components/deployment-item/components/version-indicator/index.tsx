import { FC } from "react";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";

export const VersionIndicator: FC<{
  photonId: string;
}> = ({ photonId }) => {
  const photonService = useInject(PhotonService);
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
  const latest = photonGroups.some((g) => g.id === photonId);
  return <>@{latest ? "latest" : photonId}</>;
};
