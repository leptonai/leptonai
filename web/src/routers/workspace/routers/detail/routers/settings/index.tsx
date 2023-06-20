import { Layout } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/components/layout";
import { ApiTokens } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/api-tokens";
import { General } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/general";
import { Secrets } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/secrets";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { useInject } from "@lepton-libs/di";
import { FC, useEffect } from "react";
import { Navigate, Route, Routes, useResolvedPath } from "react-router-dom";

export const Settings: FC = () => {
  const titleService = useInject(TitleService);
  const { pathname } = useResolvedPath("");

  useEffect(() => {
    titleService.setTitle("Settings");
  }, [titleService]);

  return (
    <Layout>
      <Routes>
        <Route path="general" element={<General />} />
        <Route path="api-tokens" element={<ApiTokens />} />
        <Route path="secrets" element={<Secrets />} />
        <Route
          path="*"
          element={<Navigate to={`${pathname}/general`} replace />}
        />
      </Routes>
    </Layout>
  );
};
