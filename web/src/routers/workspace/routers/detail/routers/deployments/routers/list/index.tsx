import { FC, useMemo, useState } from "react";
import { Col, Input, Row, Select, List as AntdList, Cascader } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useParams } from "react-router-dom";
import dayjs from "dayjs";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { DeploymentItem } from "../../../../../../components/deployment-item";
import { CreateDeployment } from "@lepton-dashboard/routers/workspace/components/create-deployment";

export const List: FC = () => {
  const { name } = useParams();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const theme = useAntdTheme();
  const [search, setSearch] = useState<string>("");
  const [status, setStatus] = useState<string[]>([]);
  const [photonFilters, setPhotonFilters] = useState<string[]>(
    name ? [name] : []
  );
  const photonService = useInject(PhotonService);
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
  const options = photonGroups.map((g) => {
    return {
      value: g.name,
      label: g.name,
      children: g.versions.map((i) => {
        return {
          value: i.id,
          label: dayjs(i.created_at).format("lll"),
        };
      }),
    };
  });
  const filteredDeployments = useMemo(() => {
    const [name, id] = photonFilters;
    const ids = id
      ? [id]
      : photonGroups.find((m) => m.name === name)?.versions.map((i) => i.id) ||
        [];
    return deployments.filter(
      (d) =>
        (status.length === 0 || status.indexOf(d.status.state) !== -1) &&
        JSON.stringify(d).indexOf(search) !== -1 &&
        ((ids.length > 0 && ids.indexOf(d.photon_id) !== -1) ||
          ids.length === 0)
    );
  }, [deployments, search, status, photonFilters, photonGroups]);
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
          showSearch
          value={photonFilters}
          allowClear
          placeholder="Select Photon"
          style={{ width: "100%" }}
          options={options}
          changeOnSelect
          onChange={(d) => setPhotonFilters((d as string[]) || [])}
        />
      </Col>
      <Col flex="300px">
        <Select
          style={{ width: "100%" }}
          mode="multiple"
          value={status}
          placeholder="Deployment Status"
          onChange={(v) => setStatus(v)}
          maxTagCount={1}
          options={[
            {
              label: "NOT READY",
              value: "Not Ready",
            },
            {
              label: "RUNNING",
              value: "Running",
            },
            {
              label: "STARTING",
              value: "Starting",
            },
            {
              label: "UPDATING",
              value: "Updating",
            },
          ]}
        />
      </Col>
      <Col flex="180px">
        <CreateDeployment />
      </Col>
      <Col span={24}>
        <AntdList
          rowKey="id"
          style={{
            border: `1px solid ${theme.colorBorder}`,
            boxShadow: theme.boxShadowTertiary,
            borderRadius: `${theme.borderRadius}px`,
            background: theme.colorBgContainer,
          }}
          itemLayout="horizontal"
          dataSource={filteredDeployments}
          renderItem={(deployment) => (
            <AntdList.Item style={{ padding: 0, display: "block" }}>
              <Card borderless>
                <DeploymentItem deployment={deployment} />
              </Card>
            </AntdList.Item>
          )}
        />
      </Col>
    </Row>
  );
};
