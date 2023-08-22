import { css } from "@emotion/react";
import { Layout } from "@lepton-dashboard/components/layout";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";
import { Header } from "@lepton-dashboard/components/layout/components/header";
import { Nav } from "@lepton-dashboard/routers/playground/components/nav";
import { Llama2 } from "@lepton-dashboard/routers/playground/routers/llama2";
import { ChatService } from "@lepton-libs/gradio/chat.service";
import { Button, Grid, Space } from "antd";
import { FC, Suspense } from "react";
import { Loading } from "@lepton-dashboard/components/loading";
import { Route, Routes } from "react-router-dom";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";
import { StableDiffusionXl } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl";
import { DIContainer } from "@lepton-libs/di";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";

export const Playground: FC = () => {
  const { md } = Grid.useBreakpoint();
  return (
    <DIContainer providers={[PlaygroundService, ChatService]}>
      <Suspense fallback={<Loading />}>
        <Layout
          footer={<Footer />}
          header={
            <Header
              hideDefaultActions
              enableLogoHref
              border
              actions={<Nav />}
              content={
                md ? (
                  <Space
                    css={css`
                      margin-left: 32px;
                    `}
                  >
                    <Button
                      size="small"
                      type="text"
                      href="https://lepton.ai/docs"
                      target="_blank"
                    >
                      Document
                    </Button>
                    <Button
                      size="small"
                      type="text"
                      href="https://lepton.ai/references"
                      target="_blank"
                    >
                      Reference
                    </Button>
                    <Button
                      size="small"
                      type="text"
                      href="https://github.com/leptonai/examples"
                      target="_blank"
                    >
                      Examples
                    </Button>
                  </Space>
                ) : null
              }
            />
          }
        >
          <Routes>
            <Route path="sdxl" element={<StableDiffusionXl />} />
            <Route path="llama2" element={<Llama2 />} />
            <Route path="*" element={<NavigateTo name="playgroundLLM" />} />
          </Routes>
        </Layout>
      </Suspense>
    </DIContainer>
  );
};
