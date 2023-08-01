import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC } from "react";
import { Route, Routes } from "react-router-dom";
import { List } from "@lepton-dashboard/routers/workspace/routers/detail/routers/photons/routers/list";
import styled from "@emotion/styled";
import { Detail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/photons/routers/detail";
import { Versions } from "@lepton-dashboard/routers/workspace/routers/detail/routers/photons/routers/versions";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";
const Container = styled.div`
  flex: 1 1 auto;
`;
export const Photons: FC = () => {
  useDocumentTitle("Photons");
  return (
    <Container>
      <Routes>
        <Route path="list" element={<List />} />
        <Route path="versions/:name" element={<Versions />} />
        <Route path="detail/:id" element={<Detail />} />
        <Route path="*" element={<NavigateTo name="photonsList" replace />} />
      </Routes>
    </Container>
  );
};