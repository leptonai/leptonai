import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC, lazy } from "react";
import { Navigate, Route, Routes, useResolvedPath } from "react-router-dom";
import { Container as ContainerWithNav } from "./components/container";
import styled from "@emotion/styled";

const Jobs = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/fine-tune/routers/jobs"
  ).then((e) => ({
    default: e.Jobs,
  }))
);

const Create = lazy(() =>
  import(
    "@lepton-dashboard/routers/workspace/routers/detail/routers/fine-tune/routers/create"
  ).then((e) => ({
    default: e.Create,
  }))
);

const Container = styled.div`
  flex: 1 1 auto;
`;

export const FineTune: FC = () => {
  const { pathname } = useResolvedPath("");

  useDocumentTitle("Fine Tuning");
  return (
    <Container>
      <Routes>
        <Route element={<ContainerWithNav />}>
          <Route path="jobs" element={<Jobs />} />
          <Route path="create" element={<Create />} />
          <Route
            path="*"
            element={<Navigate to={`${pathname}/create`} replace />}
          />
        </Route>
      </Routes>
    </Container>
  );
};
