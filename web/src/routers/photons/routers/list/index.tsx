import { FC, useMemo, useState } from "react";
import { Col, Empty, Input, Row, Segmented } from "antd";
import {
  AppstoreOutlined,
  BarsOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Card } from "@lepton-dashboard/components/card";
import { Upload } from "@lepton-dashboard/routers/photons/components/upload";
import { PhotonItem } from "../../../../components/photon-item";
import { StorageService } from "@lepton-dashboard/services/storage.service";

export const List: FC = () => {
  const photonService = useInject(PhotonService);
  const storageService = useInject(StorageService);
  const photonGroups = useStateFromObservable(
    () => photonService.listGroups(),
    []
  );
  const [search, setSearch] = useState<string>("");
  const [view, setView] = useState(
    storageService.get("PHOTON_LAYOUT") || "card"
  );
  const filteredPhotonGroups = useMemo(() => {
    return photonGroups.filter((e) => JSON.stringify(e).indexOf(search) !== -1);
  }, [photonGroups, search]);
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
              suffix={
                <Segmented
                  size="small"
                  value={view}
                  onChange={(v) => {
                    const layout = v as string;
                    storageService.set("PHOTON_LAYOUT", layout);
                    setView(layout);
                  }}
                  options={[
                    {
                      value: "card",
                      icon: <AppstoreOutlined />,
                    },
                    {
                      value: "list",
                      icon: <BarsOutlined />,
                    },
                  ]}
                />
              }
              placeholder="Search"
            />
          </Col>
          <Col flex="0">
            <Upload />
          </Col>
        </Row>
      </Col>
      <Col span={24}>
        {filteredPhotonGroups.length > 0 ? (
          <Row gutter={[16, 16]} wrap>
            {filteredPhotonGroups.map((group) => (
              <Col
                xs={24}
                sm={24}
                md={view === "card" ? 12 : 24}
                key={`${group.name}`}
              >
                <Card>
                  <PhotonItem photon={group} versions={group.versions} />
                </Card>
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
