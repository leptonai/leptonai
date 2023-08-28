import { css } from "@emotion/react";
import { Layout } from "@lepton-dashboard/components/layout";
import { Footer } from "@lepton-dashboard/components/layout/components/footer";
import { Header } from "@lepton-dashboard/components/layout/components/header";
import { Nav } from "@lepton-dashboard/routers/playground/components/nav";
import { Llama2 } from "@lepton-dashboard/routers/playground/routers/llama2";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { CodeLlama } from "@lepton-dashboard/routers/playground/routers/code-llama";
import { ChatService } from "@lepton-libs/gradio/chat.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Button, Grid, Space } from "antd";
import { FC, Suspense } from "react";
import { Loading } from "@lepton-dashboard/components/loading";
import { Route, Routes } from "react-router-dom";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";
import { StableDiffusionXl } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl";
import { DIContainer, useInject } from "@lepton-libs/di";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { catchError, of } from "rxjs";

export const Playground: FC = () => {
  const { md } = Grid.useBreakpoint();
  const authService = useInject(AuthService);
  const user = useStateFromObservable(
    () => authService.getUser().pipe(catchError(() => of(null))),
    null
  );
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
              actions={
                md ? (
                  <Space
                    size={30}
                    css={css`
                      position: relative;
                      top: 1px;
                      right: 1px;
                    `}
                  >
                    <Button
                      css={css`
                        padding: 0 !important;
                      `}
                      size="small"
                      type="text"
                      href="https://lepton.ai/docs"
                    >
                      Document
                    </Button>
                    <Button
                      css={css`
                        padding: 0 !important;
                      `}
                      size="small"
                      type="text"
                      href="https://lepton.ai/references"
                    >
                      Reference
                    </Button>
                    <Button
                      css={css`
                        padding: 0 !important;
                      `}
                      size="small"
                      type="text"
                      href="https://lepton.ai/pricing"
                    >
                      Pricing
                    </Button>
                    <Button
                      css={css`
                        padding: 0 !important;
                      `}
                      size="small"
                      type="text"
                    >
                      Playground
                    </Button>
                    <Button
                      css={css`
                        padding: 0 !important;
                      `}
                      size="small"
                      type="text"
                      target="_blank"
                      href="https://github.com/leptonai/examples"
                    >
                      Examples
                    </Button>
                    {user && (
                      <Button
                        css={css`
                          padding: 0 11px !important;
                          font-weight: 500 !important;
                          position: relative;
                          left: 1px;
                          top: -1px;
                          border-radius: 6px !important;
                        `}
                        size="small"
                        type="primary"
                        target="_blank"
                        href="/"
                      >
                        Dashboard
                      </Button>
                    )}
                  </Space>
                ) : null
              }
              content={<Nav />}
            />
          }
        >
          <Routes>
            <Route path="sdxl" element={<StableDiffusionXl />} />
            <Route path="llama2" element={<Llama2 />} />
            <Route path="codellama" element={<CodeLlama />} />
            <Route path="*" element={<NavigateTo name="playgroundLLM" />} />
          </Routes>
        </Layout>
      </Suspense>
    </DIContainer>
  );
};
