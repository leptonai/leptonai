import { css } from "@emotion/react";
import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ColumnsType } from "antd/es/table";
import { FC, useMemo, useState } from "react";
import {
  Col,
  Row,
  Radio,
  Tag,
  Button,
  Popconfirm,
  Table,
  Typography,
} from "antd";
import { FineTuneService } from "@lepton-dashboard/routers/workspace/services/fine-tune.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { switchMap } from "rxjs";
import { CopyFile, StopFilled } from "@carbon/icons-react";

const AllStatus = "#all";

const FilterConfig = {
  status: [
    {
      value: AllStatus,
      label: "All",
    },
    {
      value: FineTuneJobStatus.RUNNING,
      label: "RUNNING",
    },
    {
      value: FineTuneJobStatus.SUCCESS,
      label: "SUCCESS",
    },
    {
      value: FineTuneJobStatus.PENDING,
      label: "PENDING",
    },
    {
      value: FineTuneJobStatus.CANCELLED,
      label: "CANCELLED",
    },
    {
      value: FineTuneJobStatus.FAILED,
      label: "FAILED",
    },
  ],
};

const StatusTag: FC<{ status: FineTuneJobStatus }> = ({ status }) => {
  switch (status) {
    case FineTuneJobStatus.RUNNING:
      return (
        <Tag
          css={css`
            border-color: transparent !important;
          `}
          icon={<SyncOutlined spin />}
          color="processing"
          bordered={false}
        >
          RUNNING
        </Tag>
      );
    case FineTuneJobStatus.PENDING:
      return (
        <Tag
          css={css`
            border-color: transparent !important;
          `}
          icon={<ClockCircleOutlined />}
          color="default"
          bordered={false}
        >
          PENDING
        </Tag>
      );
    case FineTuneJobStatus.CANCELLED:
      return (
        <Tag
          css={css`
            border-color: transparent !important;
          `}
          icon={<MinusCircleOutlined />}
          color="default"
          bordered={false}
        >
          CANCELLED
        </Tag>
      );
    case FineTuneJobStatus.SUCCESS:
      return (
        <Tag
          css={css`
            border-color: transparent !important;
          `}
          icon={<CheckCircleOutlined />}
          color="success"
          bordered={false}
        >
          SUCCESS
        </Tag>
      );
    case FineTuneJobStatus.FAILED:
      return (
        <Tag
          css={css`
            border-color: transparent !important;
          `}
          icon={<CloseCircleOutlined />}
          color="error"
          bordered={false}
        >
          FAILED
        </Tag>
      );
    default:
      return null;
  }
};

export const Jobs: FC = () => {
  const refreshService = useInject(RefreshService);
  const fineTuneService = useInject(FineTuneService);
  const [status, setStatus] = useState<string>(AllStatus);
  const [loading, setLoading] = useState(true);

  const fineTunes = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(switchMap(() => fineTuneService.listJobs())),
    [],
    {
      next: () => {
        setLoading(false);
      },
    }
  );

  const cancelJob = (id: number) => {
    fineTuneService.cancelJob(id).subscribe({
      next: () => {
        refreshService.refresh();
      },
    });
  };

  const filteredFineTunes = useMemo(() => {
    if (status === AllStatus) {
      return fineTunes;
    }
    return fineTunes.filter((e) => e.status === status);
  }, [fineTunes, status]);

  const statusCount = useMemo(() => {
    return fineTunes.reduce(
      (acc, cur) => {
        acc[cur.status] = acc[cur.status] || 0;
        acc[cur.status]++;
        return acc;
      },
      {
        [AllStatus]: fineTunes.length,
      } as Record<FineTuneJobStatus | typeof AllStatus, number>
    );
  }, [fineTunes]);

  const columns: ColumnsType<FineTuneJob> = [
    {
      title: "Status",
      width: "120px",
      dataIndex: "status",
      render: (status) => <StatusTag status={status} />,
    },
    {
      title: "Created At",
      ellipsis: true,
      dataIndex: "created_at",
    },
    {
      title: "Modified At",
      ellipsis: true,
      dataIndex: "modified_at",
    },
    {
      title: "Output Dir",
      ellipsis: true,
      dataIndex: "output_dir",
      render: (text) => (
        <Typography.Text
          copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
        >
          {text}
        </Typography.Text>
      ),
    },
    {
      title: <ActionsHeader />,
      dataIndex: "status",
      width: "100px",
      render: (status, data) => {
        const disabled = ![
          FineTuneJobStatus.RUNNING,
          FineTuneJobStatus.PENDING,
        ].includes(status);
        return (
          <Popconfirm
            disabled={disabled}
            title="Cancel this job"
            description="Are you sure to cancel this job?"
            onConfirm={() => cancelJob(data.id)}
          >
            <Button
              disabled={disabled}
              size="small"
              key="cancel"
              type="text"
              icon={<CarbonIcon icon={<StopFilled />} />}
            >
              Cancel
            </Button>
          </Popconfirm>
        );
      },
    },
  ];

  return (
    <Row gutter={[8, 24]}>
      <Col flex={1}>
        <Radio.Group
          buttonStyle="solid"
          css={css`
            display: flex;
            width: 100%;
          `}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {FilterConfig.status.map((e) => (
            <Radio.Button
              css={css`
                flex: 1;
                text-align: center;
                text-overflow: ellipsis;
                overflow: hidden;
              `}
              key={e.value}
              value={e.value}
            >
              {e.label}&nbsp;(
              {statusCount[e.value as FineTuneJobStatus] || 0})
            </Radio.Button>
          ))}
        </Radio.Group>
      </Col>
      <Col span={24}>
        <Table
          loading={loading}
          size="small"
          dataSource={filteredFineTunes}
          rowKey="id"
          columns={columns}
        />
      </Col>
    </Row>
  );
};
