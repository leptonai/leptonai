import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Version } from "@carbon/icons-react";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
export const VersionDescription: FC<{
  versions: PhotonVersion[];
  photon: Photon;
}> = ({ versions, photon }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

  return (
    <Description.Item
      icon={<CarbonIcon icon={<Version />} />}
      description={
        <Link
          to={`/workspace/${workspaceTrackerService.name}/photons/versions/${photon.name}`}
          relative="route"
        >
          {versions.length} {versions.length > 1 ? "versions" : "version"}
        </Link>
      }
    />
  );
};
