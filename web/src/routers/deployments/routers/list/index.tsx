import { FC, useMemo, useState } from "react";
import { Col, Input, Row, Select, List as AntdList, Button } from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useNavigate } from "react-router-dom";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";

export const List: FC = () => {
  const deploymentService = useInject(DeploymentService);
  const navigate = useNavigate();
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const theme = useAntdTheme();
  const [search, setSearch] = useState<string>("");
  const [status, setStatus] = useState<string[]>(["starting", "running"]);
  const filteredDeployments = useMemo(() => {
    return deployments.filter(
      (d) =>
        status.indexOf(d.status.state) !== -1 &&
        JSON.stringify(d).indexOf(search) !== -1
    );
  }, [deployments, search, status]);
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
          style={{ border: `1px solid ${theme.colorBorder}` }}
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
