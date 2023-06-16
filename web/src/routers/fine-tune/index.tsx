import { Nav } from "@lepton-dashboard/routers/fine-tune/components/nav";
import { FC, lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DIContainer, useInject } from "@lepton-libs/di";

import { Loading } from "@lepton-dashboard/components/loading";
import { FineTuneService } from "@lepton-dashboard/routers/fine-tune/services/fine-tune.service";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";
import { Header } from "@lepton-dashboard/components/layout/components/header";

import { Layout } from "@lepton-dashboard/components/layout";
import { TitleService } from "@lepton-dashboard/services/title.service";

const Jobs = lazy(() =>
  import("@lepton-dashboard/routers/fine-tune/routers/jobs").then((e) => ({
    default: e.Jobs,
  }))
);

const Create = lazy(() =>
  import("@lepton-dashboard/routers/fine-tune/routers/create").then((e) => ({
    default: e.Create,
  }))
);

export const FineTune: FC = () => {
  const titleService = useInject(TitleService);
  useEffect(() => {
    titleService.setTitle("Fine Tuning");
  }, [titleService]);
  return (
    <DIContainer providers={[FineTuneService]}>
      <Layout footer={<Footer />} header={<Header />} nav={<Nav />}>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="jobs" element={<Jobs />} />
            <Route path="create" element={<Create />} />
            <Route path="*" element={<Navigate to="/create" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </DIContainer>
  );
};
