import { Container } from "@lepton-dashboard/routers/playground/components/container";
import { ImageResult } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/image-result";
import {
  Options,
  SdxlOption,
} from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/options";
import { presets } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/presets";
import { APICodeTemplate } from "@lepton-libs/gradio/api-code-template";
import { PromptInput } from "@lepton-libs/gradio/prompt-input";
import { FC, useMemo, useRef, useState } from "react";
import { css } from "@emotion/react";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Image, MagicWandFilled } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { MetaService } from "@lepton-dashboard/services/meta.service";
import { PresetSelector } from "@lepton-dashboard/routers/playground/components/preset-selector";
import { Api } from "@lepton-dashboard/routers/playground/components/api";
import { tap } from "rxjs";

const presetOptions = presets.map((p) => ({
  label: p.name,
  value: p.prompt,
  placeholder: "Load a preset",
}));

const getRandom = () => {
  return Math.floor(Math.random() * 2147483647);
};

export const StableDiffusionXl: FC = () => {
  const theme = useAntdTheme();
  const metaService = useInject(MetaService);
  metaService.setTitle("🏞️ Stable Diffusion XL", true);
  metaService.setURLPath();
  const [loading, setLoading] = useState(false);
  const [hasResponse, setHasResponse] = useState(false);
  const abortController = useRef<AbortController | null>(null);
  const [result, setResult] = useState<string | null>(presets[0].image);
  const [error, setError] = useState<string | null>(null);
  const playgroundService = useInject(PlaygroundService);
  const [prompt, setPrompt] = useState(presets[0].prompt);
  const [url, setUrl] = useState<string>("");
  const [option, setOption] = useState<SdxlOption>({
    width: 1024,
    height: 1024,
    seed: getRandom(),
    steps: 30,
    use_refiner: false,
    random_seed: true,
  });

  const backend = useStateFromObservable(
    () =>
      playgroundService.getStableDiffusionXlBackend().pipe(
        tap((url) => {
          setUrl(url);
        })
      ),
    null
  );

  const presetPrompt = useMemo(() => {
    if (presets.some((p) => p.prompt === prompt)) {
      return prompt;
    } else {
      return undefined;
    }
  }, [prompt]);

  const submit = () => {
    if (!backend) {
      return;
    }
    setResult(null);
    abortController.current = new AbortController();
    setLoading(true);
    setHasResponse(false);
    const { random_seed, ...options } = option;
    let sendOptions = options;
    if (random_seed) {
      sendOptions = { ...sendOptions, seed: getRandom() };
    }
    setOption({ ...sendOptions, random_seed });
    fetch(backend, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...sendOptions,
        prompt,
      }),
      signal: abortController.current.signal,
    })
      .then((res) => {
        if (res.ok) {
          setHasResponse(false);
          return res.blob();
        } else {
          setError(`HTTP ${res.status}: ${res.statusText}`);
        }
      })
      .then((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          setResult(url);
        } else {
          setResult(null);
        }
      })
      .catch((e) => {
        setError(e?.message);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const cancel = () => {
    abortController.current?.abort();
  };

  const codes = Object.entries(APICodeTemplate.sd(url)).map(
    ([language, code]) => ({ language, code })
  );

  return (
    <Container
      loading={!backend}
      icon={<CarbonIcon icon={<Image />} />}
      title={
        <span
          css={css`
            @media (max-width: 480px) {
              max-width: 80px;
              overflow: hidden;
              text-overflow: ellipsis;
            }
          `}
        >
          Stable Diffusion XL
        </span>
      }
      extra={
        <>
          <PresetSelector
            options={presetOptions}
            value={presetPrompt}
            onChange={(v) => {
              setPrompt(v);
              setResult(presets.find((p) => p.prompt === v)!.image);
            }}
          />
          <Api name="Stable Diffusion XL" codes={codes} />
        </>
      }
      option={<Options value={option} onChange={setOption} />}
      content={
        <div
          css={css`
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            position: relative;
          `}
        >
          <PromptInput
            css={css`
              margin-bottom: 16px;
              flex: 0 0 auto;
            `}
            submitIcon={<CarbonIcon icon={<MagicWandFilled />} />}
            submitText="Generate"
            loading={loading}
            value={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            onCancel={cancel}
          />
          <div
            css={css`
              position: relative;
              background: ${theme.colorBgContainer};
              border-radius: ${theme.borderRadius}px;
              overflow: hidden;
              padding: 8px;
              min-height: 350px;
              flex: 1 1 auto;
              display: flex;
              justify-content: center;
              align-items: center;
            `}
          >
            <div
              css={css`
                position: absolute;
                inset: 0;
                background-image: url("${result}");
                background-repeat: no-repeat;
                background-size: cover;
                background-position: center;
                text-align: center;
              `}
            >
              <ImageResult
                hasResponse={hasResponse}
                error={error}
                result={result}
                prompt={prompt}
                loading={loading}
              />
            </div>
          </div>
        </div>
      }
    />
  );
};
