import { Container } from "@lepton-dashboard/routers/playground/components/container";
import {
  Options,
  SdxlOption,
} from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/options";
import { presets } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/presets";
import { PromptInput } from "@lepton-libs/gradio/prompt-input";
import { FC, useMemo, useRef, useState } from "react";
import { Button, Typography, Image as AntdImage, Select } from "antd";
import { css } from "@emotion/react";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Download, Image, MagicWandFilled } from "@carbon/icons-react";
import { Stopwatch } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/stopwatch";
import { CarbonIcon } from "@lepton-dashboard/components/icons";

const presetOptions = presets.map((p) => ({
  label: p.name,
  value: p.prompt,
  placeholder: "Load a preset",
}));

export const StableDiffusionXl: FC = () => {
  const theme = useAntdTheme();
  const [loading, setLoading] = useState(false);
  const abortController = useRef<AbortController | null>(null);
  const [result, setResult] = useState<string | null>(presets[0].image);
  const [error, setError] = useState<string | null>(null);
  const playgroundService = useInject(PlaygroundService);
  const [prompt, setPrompt] = useState(presets[0].prompt);
  const [option, setOption] = useState<SdxlOption>({
    width: 768,
    height: 768,
    seed: 245967316,
    num_inference_steps: 25,
    use_refiner: true,
  });

  const backend = useStateFromObservable(
    () => playgroundService.getStableDiffusionXlBackend(),
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
    fetch(backend, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...option,
        prompt,
      }),
      signal: abortController.current.signal,
    })
      .then((res) => {
        if (res.ok) {
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
          setError("No result");
        }
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const cancel = () => {
    abortController.current?.abort();
  };

  return (
    <Container
      loading={!backend}
      icon={<CarbonIcon icon={<Image />} />}
      title="Stable Diffusion XL"
      extra={
        <Select
          css={css`
            width: 160px;
            .ant-select-selection-placeholder,
            .ant-select-arrow {
              font-weight: normal;
              color: ${theme.colorText};
            }
          `}
          popupMatchSelectWidth={false}
          options={presetOptions}
          optionLabelProp="placeholder"
          value={presetPrompt}
          onChange={(v) => {
            setPrompt(v);
            setResult(presets.find((p) => p.prompt === v)!.image);
          }}
          size="small"
          showSearch
          bordered={false}
          placeholder="Load a preset"
        />
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
              border: 1px solid ${theme.colorBorder};
              background: ${theme.colorBgContainer};
              border-radius: ${theme.borderRadius}px;
              padding: 8px;
              min-height: 350px;
              flex: 1 1 auto;
              display: flex;
              justify-content: center;
              align-items: center;
              img {
                width: auto;
                max-width: 100%;
                max-height: calc(max(60vh, 300px));
                border-radius: ${theme.borderRadius}px;
              }
            `}
          >
            {result ? (
              <>
                <div
                  css={css`
                    position: absolute;
                    inset: 0;
                    background-image: url("${result}");
                    background-repeat: no-repeat;
                    background-size: cover;
                    background-position: center;
                  `}
                />
                <div
                  css={css`
                    position: absolute;
                    inset: 0;
                    backdrop-filter: blur(100px);
                  `}
                />
                <Button
                  css={css`
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    z-index: 1;
                  `}
                  download
                  href={result}
                  target="_blank"
                  size="small"
                  icon={<CarbonIcon icon={<Download />} />}
                />
                <AntdImage width="auto" alt={prompt || ""} src={result} />
              </>
            ) : error ? (
              <Typography.Text type="danger">{error}</Typography.Text>
            ) : (
              <div
                css={css`
                  color: ${theme.colorTextSecondary};
                `}
              >
                {loading ? (
                  <Typography.Text type="secondary">
                    Generating... (<Stopwatch start />)
                  </Typography.Text>
                ) : (
                  <div
                    css={css`
                      display: flex;
                      flex: 1;
                      height: 100%;
                      flex-direction: column;
                      justify-content: center;
                      align-items: center;
                      font-size: 128px;
                      opacity: 0.3;
                      color: ${theme.colorBorderSecondary};
                    `}
                  >
                    <CarbonIcon icon={<Image />} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      }
    />
  );
};
