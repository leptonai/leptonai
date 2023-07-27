import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import styled from "@emotion/styled";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

const List = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/list"
  ).then((e) => ({
    default: e.List,
  }))
);

const ModelComparison = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/model-comparison"
  ).then((e) => ({
    default: e.ModelComparison,
  }))
);

const Container = styled.div`
  flex: 1 1 auto;
`;

export const Tuna: FC = () => {
  useDocumentTitle("TUNA");
  return (
    <Container>
      <Routes>
        <Route>
          <Route path="list" element={<List />} />
          <Route path="chat/:name" element={<ModelComparison />} />
          <Route path="*" element={<NavigateTo name="tunaList" replace />} />
        </Route>
      </Routes>
    </Container>
  );
};
