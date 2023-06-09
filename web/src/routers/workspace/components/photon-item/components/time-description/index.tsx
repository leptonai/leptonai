import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Time } from "@carbon/icons-react";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { DateParser } from "@lepton-dashboard/routers/workspace/components/date-parser";
import { useInject } from "@lepton-libs/di";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";

export const TimeDescription: FC<{
  versions?: PhotonVersion[];
  photon: Photon;
  detail: boolean;
}> = ({ versions, photon }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);

  return (
    <Description.Item
      icon={<CarbonIcon icon={<Time />} />}
      description={
        <Link
          to={`/workspace/${workspaceTrackerService.name}/photons/detail/${photon.id}`}
          relative="route"
        >
          <DateParser
            prefix={versions && versions.length > 1 ? "Updated" : "Created"}
            date={photon.created_at}
          />
        </Link>
      }
    />
  );
};
