import { FC, useMemo, useState } from "react";
import styled from "@emotion/styled";
import { Col, Input, Row } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Card } from "@lepton-dashboard/routers/models/components/card";

const Filter = styled.div`
  display: flex;
  width: 100%;
  margin-bottom: 24px;
`;

const Search = styled.div`
  flex: 1 1 auto;
`;

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
    <>
      <Filter>
        <Search>
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            prefix={<SearchOutlined />}
            placeholder="Search"
          />
        </Search>
      </Filter>
      <Row gutter={[16, 16]} wrap>
        {filteredModels.map((group) => (
          <Col flex="1" key={group.name}>
            <Card group={group} />
          </Col>
        ))}
      </Row>
    </>
  );
};
