import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import dayjs from "dayjs";
import { FC } from "react";

export const PhotonLabel: FC<{
  id: string;
  name: string;
  created_at: number;
  showTime?: boolean;
  showName?: boolean;
}> = ({ id, name, created_at, showTime = false, showName = false }) => {
  const photonService = useInject(PhotonService);
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
  const latest = photonGroups.some((g) => g.id === id);
  const displayId = latest ? "latest" : id.replace(`${name}-`, "");
  return (
    <>
      {showName && <>{`${name}@`}</>}
      <>{`${displayId}`}</>
      {showTime && <> / {dayjs(created_at).format("lll")}</>}
    </>
  );
};
