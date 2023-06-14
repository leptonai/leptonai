import { FC, lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DIContainer, useInject } from "@lepton-libs/di";

import { Loading } from "@lepton-dashboard/components/loading";
import { FineTuneService } from "@lepton-dashboard/routers/fine-tune/services/fine-tune.service";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";
import { Header } from "@lepton-dashboard/components/layout/components/header";

import { Layout } from "@lepton-dashboard/components/layout";
import { Breadcrumb as AntdBreadcrumb } from "antd";
import { HomeOutlined } from "@ant-design/icons";
import styled from "@emotion/styled";
import { TitleService } from "@lepton-dashboard/services/title.service";

const Jobs = lazy(() =>
  import("@lepton-dashboard/routers/fine-tune/routers/jobs").then((e) => ({
    default: e.Jobs,
  }))
);

const Breadcrumb = styled(AntdBreadcrumb)`
  padding: 24px 24px 0;
`;

export const FineTune: FC = () => {
  const titleService = useInject(TitleService);
  titleService.setTitle("Fine Tuning");
  return (
    <DIContainer providers={[FineTuneService]}>
      <Layout
        footer={<Footer />}
        header={<Header />}
        nav={
          <Breadcrumb
            items={[
              {
                href: "/",
                title: <HomeOutlined />,
              },
              {
                title: "Fine Tuning",
              },
            ]}
          />
        }
      >
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="jobs" element={<Jobs />} />
            <Route path="*" element={<Navigate to="./jobs" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </DIContainer>
  );
};
