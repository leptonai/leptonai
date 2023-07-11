import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { FC, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Container as ContainerWithNav } from "./components/container";
import styled from "@emotion/styled";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

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
  useDocumentTitle("Fine Tuning");
  return (
    <Container>
      <Routes>
        <Route element={<ContainerWithNav />}>
          <Route path="jobs" element={<Jobs />} />
          <Route path="create" element={<Create />} />
          <Route
            path="*"
            element={<NavigateTo name="fineTuneCreate" replace />}
          />
        </Route>
      </Routes>
    </Container>
  );
};
