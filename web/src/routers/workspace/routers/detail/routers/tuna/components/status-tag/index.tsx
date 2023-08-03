import { SmallTag } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/small-tag";
import { FC } from "react";
import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";

export const StatusTag: FC<{ status: FineTuneJobStatus }> = ({ status }) => {
  switch (status) {
    case FineTuneJobStatus.RUNNING:
      return <SmallTag color="processing">RUNNING</SmallTag>;
    case FineTuneJobStatus.PENDING:
      return <SmallTag color="default">PENDING</SmallTag>;
    case FineTuneJobStatus.CANCELLED:
      return <SmallTag color="default">CANCELLED</SmallTag>;
    case FineTuneJobStatus.SUCCESS:
      return <SmallTag color="success">SUCCESS</SmallTag>;
    case FineTuneJobStatus.FAILED:
      return <SmallTag color="error">FAILED</SmallTag>;
    default:
      return null;
  }
};
