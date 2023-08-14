import { Network_1 } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ProcessingWrapper } from "@lepton-dashboard/components/processing-wrapper";
import { SmallTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/small-tag";
import { FC } from "react";
import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";

export const TunaStatus: FC<{ status: FineTuneJobStatus }> = ({ status }) => {
  switch (status) {
    case FineTuneJobStatus.RUNNING:
      return (
        <ProcessingWrapper processing>
          <SmallTag
            icon={<CarbonIcon icon={<Network_1 />} />}
            color="processing"
          >
            RUNNING
          </SmallTag>
        </ProcessingWrapper>
      );
    case FineTuneJobStatus.PENDING:
      return (
        <ProcessingWrapper processing>
          <SmallTag icon={<CarbonIcon icon={<Network_1 />} />} color="default">
            PENDING
          </SmallTag>
        </ProcessingWrapper>
      );
    case FineTuneJobStatus.CANCELLED:
      return (
        <SmallTag icon={<CarbonIcon icon={<Network_1 />} />} color="default">
          CANCELLED
        </SmallTag>
      );
    case FineTuneJobStatus.SUCCESS:
      return (
        <SmallTag icon={<CarbonIcon icon={<Network_1 />} />} color="success">
          SUCCESS
        </SmallTag>
      );
    case FineTuneJobStatus.FAILED:
      return (
        <SmallTag icon={<CarbonIcon icon={<Network_1 />} />} color="error">
          FAILED
        </SmallTag>
      );
    default:
      return null;
  }
};
