import {
  FullLayoutWidth,
  LimitedLayoutWidth,
} from "@lepton-dashboard/components/layout";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { List } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/list";
import { Chat } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/routers/chat";
import { FC } from "react";
import { Route, Routes } from "react-router-dom";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Tuna: FC = () => {
  useDocumentTitle("Tuna");
  return (
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
              <Chat />
            </FullLayoutWidth>
          }
        />
        <Route path="*" element={<NavigateTo name="tunaList" replace />} />
      </Route>
    </Routes>
  );
};
