import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC } from "react";
import { Route, Routes } from "react-router-dom";
import { List } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/list";
import styled from "@emotion/styled";
import { Detail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

const Container = styled.div`
  flex: 1 1 auto;
`;
export const Deployments: FC = () => {
  useDocumentTitle("Deployments");

  return (
    <Container>
      <Routes>
        <Route path="list/:photonName?" element={<List />} />
        <Route path="detail/:name/*" element={<Detail />} />
        <Route
          path="*"
          element={<NavigateTo name="deploymentsList" replace />}
        />
      </Routes>
    </Container>
  );
};
