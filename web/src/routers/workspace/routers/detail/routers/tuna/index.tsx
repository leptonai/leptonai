import {
  FullLayoutWidth,
  LimitedLayoutWidth,
} from "@lepton-dashboard/components/layout";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { List } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/list";
import { ModelComparison } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/model-comparison";
import { FC } from "react";
import { Route, Routes } from "react-router-dom";
import styled from "@emotion/styled";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";
import { DIContainer } from "@lepton-libs/di";
import { ChatService } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";

const Container = styled.div`
  flex: 1 1 auto;
`;

export const Tuna: FC = () => {
  useDocumentTitle("Tuna");
  return (
    <DIContainer providers={[ChatService]}>
      <Container>
        <Routes>
          <Route>
            <Route
              path="list"
              element={
                <LimitedLayoutWidth>
                  <List />
                </LimitedLayoutWidth>
              }
            />
            <Route
              path="chat/:name"
              element={
                <FullLayoutWidth>
                  <ModelComparison />
                </FullLayoutWidth>
              }
            />
            <Route path="*" element={<NavigateTo name="tunaList" replace />} />
          </Route>
        </Routes>
      </Container>
    </DIContainer>
  );
};
