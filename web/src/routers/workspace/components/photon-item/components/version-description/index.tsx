import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Version } from "@carbon/icons-react";
import { LinkTo } from "@lepton-dashboard/components/link-to";
export const VersionDescription: FC<{
  versions: PhotonVersion[];
  photon: Photon;
}> = ({ versions, photon }) => {
  return (
    <Description.Item
      icon={<CarbonIcon icon={<Version />} />}
      description={
        <LinkTo
          name="photonVersions"
          params={{
            photonId: photon.name,
          }}
          relative="route"
        >
          {versions.length} {versions.length > 1 ? "versions" : "version"}
        </LinkTo>
      }
    />
  );
};
