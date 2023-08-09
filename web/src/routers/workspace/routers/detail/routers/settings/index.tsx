import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { Layout } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/components/layout";
import { ApiTokens } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/api-tokens";
import { Billing } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing";
import { General } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/general";
import { Secrets } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/secrets";
import { Registries } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/registries";
import { FC } from "react";
import { Route, Routes } from "react-router-dom";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Settings: FC = () => {
  useDocumentTitle("Settings");

  return (
    <Layout>
      <Routes>
        <Route path="general" element={<General />} />
        <Route path="api-tokens" element={<ApiTokens />} />
        <Route path="secrets" element={<Secrets />} />
        <Route path="registries" element={<Registries />} />
        <Route path="billing" element={<Billing />} />
        <Route
          path="*"
          element={<NavigateTo name="settingsGeneral" replace />}
        />
      </Routes>
    </Layout>
  );
};
