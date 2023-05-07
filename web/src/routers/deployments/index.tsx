import { FC, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { List } from "@lepton-dashboard/routers/deployments/routers/list";
import styled from "@emotion/styled";
import { Detail } from "@lepton-dashboard/routers/deployments/routers/detail";
import { useInject } from "@lepton-libs/di";
import { Create } from "@lepton-dashboard/routers/deployments/routers/create";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";

const Container = styled.div`
  flex: 1 1 auto;
`;
export const Deployments: FC = () => {
  const titleService = useInject(TitleService);
  useEffect(() => {
    titleService.setTitle("Deployments");
  }, [titleService]);
  return (
    <Container>
      <Routes>
        <Route path="create/:id?" element={<Create />} />
        <Route path="list/:name?" element={<List />} />
        <Route path="detail/:id/mode/:mode" element={<Detail />} />
        <Route path="*" element={<Navigate to="list" replace />} />
      </Routes>
    </Container>
  );
};
