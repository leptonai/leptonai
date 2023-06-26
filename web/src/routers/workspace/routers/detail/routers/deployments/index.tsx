import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC } from "react";
import { Navigate, Route, Routes, useResolvedPath } from "react-router-dom";
import { List } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/list";
import styled from "@emotion/styled";
import { Detail } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail";

const Container = styled.div`
  flex: 1 1 auto;
`;
export const Deployments: FC = () => {
  const { pathname } = useResolvedPath("");
  useDocumentTitle("Deployments");

  return (
    <Container>
      <Routes>
        <Route path="list/:name?" element={<List />} />
        <Route path="detail/:id/*" element={<Detail />} />
        <Route
          path="*"
          element={<Navigate to={`${pathname}/list`} replace />}
        />
      </Routes>
    </Container>
  );
};
