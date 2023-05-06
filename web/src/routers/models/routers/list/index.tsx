import { FC, useMemo, useState } from "react";
import { Col, Input, Row } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { ModelGroupCard } from "../../../../components/model-group-card";

export const List: FC = () => {
  const modelService = useInject(ModelService);
  const groupedModels = useStateFromObservable(
    () => modelService.listGroup(),
    []
  );
  const [search, setSearch] = useState<string>("");
  const filteredModels = useMemo(() => {
    return groupedModels.filter(
      (e) => JSON.stringify(e).indexOf(search) !== -1
    );
  }, [groupedModels, search]);
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
      <Col span={24}>
        <Row gutter={[16, 16]} wrap>
          {filteredModels.map((group) => (
            <Col flex="1" key={group.name}>
              <ModelGroupCard group={group} />
            </Col>
          ))}
        </Row>
      </Col>
    </Row>
  );
};
