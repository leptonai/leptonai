import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Version } from "@carbon/icons-react";
import { Link } from "@lepton-dashboard/components/link";

export const VersionDescription: FC<{
  versions: PhotonVersion[];
  photon: Photon;
}> = ({ versions, photon }) => {
  return (
    <Description.Item
      icon={<CarbonIcon icon={<Version />} />}
      description={
        <Link to={`/photons/versions/${photon.name}`} relative="route">
          {versions.length} {versions.length > 1 ? "versions" : "version"}
        </Link>
      }
    />
  );
};
