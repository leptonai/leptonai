import { FC, useMemo, useState } from "react";
import {
  Col,
  Input,
  Row,
  Select,
  List as AntdList,
  Button,
  Cascader,
} from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useNavigate, useParams } from "react-router-dom";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";
import dayjs from "dayjs";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";

export const List: FC = () => {
  const { name } = useParams();
  const deploymentService = useInject(DeploymentService);
  const navigate = useNavigate();
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const theme = useAntdTheme();
  const [search, setSearch] = useState<string>("");
  const [status, setStatus] = useState<string[]>(["starting", "running"]);
  const [modelFilters, setModelFilters] = useState<string[]>(
    name ? [name] : []
  );
  const modelService = useInject(ModelService);
  const groupedModels = useStateFromObservable(() => modelService.groups(), []);
  const options = groupedModels.map((g) => {
    return {
      value: g.name,
      label: g.name,
      children: g.data.map((i) => {
        return {
          value: i.id,
          label: dayjs(i.created_at).format("lll"),
        };
      }),
    };
  });
  const filteredDeployments = useMemo(() => {
    const [name, id] = modelFilters;
    const ids = id
      ? [id]
      : groupedModels.find((m) => m.name === name)?.data.map((i) => i.id) || [];
    return deployments.filter(
      (d) =>
        status.indexOf(d.status.state) !== -1 &&
        JSON.stringify(d).indexOf(search) !== -1 &&
        ((ids.length > 0 && ids.indexOf(d.photon_id) !== -1) ||
          ids.length === 0)
    );
  }, [deployments, search, status, modelFilters, groupedModels]);
  return (
    <Row gutter={[8, 24]}>
      <Col flex={1}>
        <Input
          autoFocus
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          prefix={<SearchOutlined />}
          placeholder="Search"
        />
      </Col>
      <Col flex="200px">
        <Cascader
          value={modelFilters}
          allowClear
          placeholder="Select Model"
          style={{ width: "100%" }}
          options={options}
          changeOnSelect
          onChange={(d) => setModelFilters((d as string[]) || [])}
        />
      </Col>
      <Col flex="300px">
        <Select
          style={{ width: "100%" }}
          mode="multiple"
          value={status}
          onChange={(v) => v.length > 0 && setStatus(v)}
          options={[
            {
              label: "STARTING",
              value: "starting",
            },
            {
              label: "RUNNING",
              value: "running",
            },
          ]}
        />
      </Col>
      <Col flex="180px">
        <Button
          block
          icon={<PlusOutlined />}
          onClick={() => navigate("../create", { relative: "path" })}
        >
          Create Deployment
        </Button>
      </Col>
      <Col span={24}>
        <AntdList
          style={{
            border: `1px solid ${theme.colorBorder}`,
            boxShadow: theme.boxShadowTertiary,
          }}
          itemLayout="horizontal"
          dataSource={filteredDeployments}
          renderItem={(deployment) => (
            <AntdList.Item style={{ padding: 0, display: "block" }}>
              <DeploymentCard deployment={deployment} borderless />
            </AntdList.Item>
          )}
        />
      </Col>
    </Row>
  );
};
