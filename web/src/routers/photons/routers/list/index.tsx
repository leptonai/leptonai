import { FC, useMemo, useState } from "react";
import { Col, Empty, Input, Row } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { PhotonGroupCard } from "../../../../components/photon-group-card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { Card } from "@lepton-dashboard/components/card";
import { Upload } from "@lepton-dashboard/routers/photons/components/upload";

export const List: FC = () => {
  const photonService = useInject(PhotonService);
  const groupedPhotons = useStateFromObservable(
    () => photonService.groups(),
    []
  );
  const [search, setSearch] = useState<string>("");
  const filteredPhotons = useMemo(() => {
    return groupedPhotons.filter(
      (e) => JSON.stringify(e).indexOf(search) !== -1
    );
  }, [groupedPhotons, search]);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  return (
    <Row gutter={[8, 24]}>
      <Col flex={1}>
        <Row gutter={[8, 24]}>
          <Col flex="auto">
            <Input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              prefix={<SearchOutlined />}
              placeholder="Search"
            />
          </Col>
          <Col flex="0">
            <Upload />
          </Col>
        </Row>
      </Col>
      <Col span={24}>
        {filteredPhotons.length > 0 ? (
          <Row gutter={[16, 16]} wrap>
            {filteredPhotons.map((group) => (
              <Col xs={24} sm={24} md={12} lg={12} xl={12} key={group.name}>
                <PhotonGroupCard
                  deploymentCount={
                    deployments.filter((i) =>
                      group.data.some((m) => m.id === i.photon_id)
                    ).length
                  }
                  group={group}
                />
              </Col>
            ))}
          </Row>
        ) : (
          <Card>
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </Card>
        )}
      </Col>
    </Row>
  );
};
