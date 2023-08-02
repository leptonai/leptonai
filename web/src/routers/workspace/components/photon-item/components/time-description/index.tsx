import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Time } from "@carbon/icons-react";
import { DateParser } from "../../../../../../components/date-parser";

export const TimeDescription: FC<{
  versions?: PhotonVersion[];
  photon: Photon;
  detail: boolean;
}> = ({ versions, photon }) => {
  return (
    <Description.Item
      icon={<CarbonIcon icon={<Time />} />}
      description={
        <DateParser
          prefix={versions && versions.length > 1 ? "Updated" : "Created"}
          date={photon.created_at}
        />
      }
    />
  );
};
