import { FC, useMemo, useState } from "react";
import {
  Col,
  Empty,
  Row,
  Radio,
  List,
  Tag,
  Space,
  Divider,
  Button,
  Card,
  Popconfirm,
} from "antd";
import { FineTuneService } from "@lepton-dashboard/routers/fine-tune/services/fine-tune.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FineTuneJobStatus } from "@lepton-dashboard/interfaces/fine-tune";
import { Upload } from "@lepton-dashboard/routers/fine-tune/routers/jobs/components/upload";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { switchMap } from "rxjs";

const AllStatus = "#all";

const FilterConfig = {
  status: [
    {
      value: AllStatus,
      label: "All",
    },
    {
      value: FineTuneJobStatus.RUNNING,
      label: "Running",
    },
    {
      value: FineTuneJobStatus.Pending,
      label: "Pending",
    },
    {
      value: FineTuneJobStatus.CANCELLED,
      label: "Cancelled",
    },
    {
      value: FineTuneJobStatus.SUCCESS,
      label: "Success",
    },
    {
      value: FineTuneJobStatus.FAILED,
      label: "Failed",
    },
  ],
};

const StatusTag: FC<{ status: FineTuneJobStatus }> = ({ status }) => {
  switch (status) {
    case FineTuneJobStatus.RUNNING:
      return (
        <Tag icon={<SyncOutlined spin />} color="processing">
          running
        </Tag>
      );
    case FineTuneJobStatus.Pending:
      return (
        <Tag icon={<ClockCircleOutlined />} color="default">
          pending
        </Tag>
      );
    case FineTuneJobStatus.CANCELLED:
      return (
        <Tag icon={<MinusCircleOutlined />} color="default">
          cancelled
        </Tag>
      );
    case FineTuneJobStatus.SUCCESS:
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          success
        </Tag>
      );
    case FineTuneJobStatus.FAILED:
      return (
        <Tag icon={<CloseCircleOutlined />} color="error">
          failed
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

  return (
    <Row gutter={[8, 24]}>
      <Col flex={1}>
        <Row gutter={[8, 24]}>
          <Col flex="auto">
            <Radio.Group
              buttonStyle="solid"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {FilterConfig.status.map((e) => (
                <Radio.Button key={e.value} value={e.value}>
                  {e.value === AllStatus ? <strong>{e.label}</strong> : e.label}
                  &nbsp;({statusCount[e.value as FineTuneJobStatus] || 0})
                </Radio.Button>
              ))}
            </Radio.Group>
          </Col>
          <Col flex="0">
            <Upload />
          </Col>
        </Row>
      </Col>
      <Col span={24}>
        <Card size="small">
          {filteredFineTunes.length > 0 || loading ? (
            <List
              loading={loading}
              size="small"
              itemLayout="horizontal"
              dataSource={filteredFineTunes}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    [
                      FineTuneJobStatus.RUNNING,
                      FineTuneJobStatus.Pending,
                    ].includes(item.status) ? (
                      <Popconfirm
                        title="Cancel this job"
                        description="Are you sure to cancel this job?"
                        onConfirm={() => cancelJob(item.id)}
                      >
                        <Button key="cancel" type="link" danger>
                          Cancel
                        </Button>
                      </Popconfirm>
                    ) : null,
                  ]}
                >
                  <List.Item.Meta
                    title={item.id}
                    description={
                      <Space size={0} split={<Divider type="vertical" />}>
                        <StatusTag status={item.status} />
                        <DateParser
                          prefix="Created at"
                          date={item.created_at}
                        />
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Col>
    </Row>
  );
};
