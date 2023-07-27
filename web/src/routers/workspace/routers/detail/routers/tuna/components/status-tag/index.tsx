import { FC } from "react";
import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";
import { Tag } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";

export const StatusTag: FC<{ status: FineTuneJobStatus }> = ({ status }) => {
  switch (status) {
    case FineTuneJobStatus.RUNNING:
      return (
        <Tag icon={<SyncOutlined spin />} color="processing">
          RUNNING
        </Tag>
      );
    case FineTuneJobStatus.PENDING:
      return (
        <Tag icon={<ClockCircleOutlined />} color="default">
          PENDING
        </Tag>
      );
    case FineTuneJobStatus.CANCELLED:
      return (
        <Tag icon={<MinusCircleOutlined />} color="default">
          CANCELLED
        </Tag>
      );
    case FineTuneJobStatus.SUCCESS:
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          SUCCESS
        </Tag>
      );
    case FineTuneJobStatus.FAILED:
      return (
        <Tag icon={<CloseCircleOutlined />} color="error">
          FAILED
        </Tag>
      );
    default:
      return null;
  }
};
