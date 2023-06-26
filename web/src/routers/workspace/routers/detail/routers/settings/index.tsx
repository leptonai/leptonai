import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { Layout } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/components/layout";
import { ApiTokens } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/api-tokens";
import { General } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/general";
import { FC } from "react";
import { Navigate, Route, Routes, useResolvedPath } from "react-router-dom";

export const Settings: FC = () => {
  const { pathname } = useResolvedPath("");

  useDocumentTitle("Settings");

  return (
    <Layout>
      <Routes>
        <Route path="general" element={<General />} />
        <Route path="api-tokens" element={<ApiTokens />} />
        <Route
          path="*"
          element={<Navigate to={`${pathname}/general`} replace />}
        />
      </Routes>
    </Layout>
  );
};
