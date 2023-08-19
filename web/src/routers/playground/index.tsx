import { FC, Suspense } from "react";
import { Loading } from "@lepton-dashboard/components/loading";
import { Route, Routes } from "react-router-dom";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";
import { StableDiffusionXl } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl";
import { DIContainer } from "@lepton-libs/di";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";

export const Playground: FC = () => {
  return (
    <DIContainer providers={[PlaygroundService]}>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="sdxl" element={<StableDiffusionXl />} />
          <Route path="*" element={<NavigateTo name="playgroundSDXL" />} />
        </Routes>
      </Suspense>
    </DIContainer>
  );
};
