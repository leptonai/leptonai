import { Container } from "@lepton-dashboard/routers/playground/components/container";
import {
  Options,
  SdxlOption,
} from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/options";
import { PromptInput } from "@lepton-libs/gradio/prompt-input";
import { FC, useRef, useState } from "react";
import { Button, Typography, Image as AntdImage } from "antd";
import { css } from "@emotion/react";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Download, Image, MagicWandFilled } from "@carbon/icons-react";
import { Stopwatch } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/stopwatch";
import { CarbonIcon } from "@lepton-dashboard/components/icons";

export const StableDiffusionXl: FC = () => {
  const theme = useAntdTheme();
  const [loading, setLoading] = useState(false);
  const abortController = useRef<AbortController | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const playgroundService = useInject(PlaygroundService);
  const [prompt, setPrompt] = useState(
    "A majestic lion jumping from a big stone at night"
  );
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

  const submit = () => {
    if (!backend) {
      return;
    }
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
      title="Stable Diffusion XL Playground"
      option={<Options value={option} onChange={setOption} />}
      content={
        <>
          <PromptInput
            css={css`
              margin-bottom: 16px;
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
              padding: 16px;
              min-height: 350px;
              display: flex;
              justify-content: center;
              align-items: center;
              img {
                width: auto;
                max-width: 100%;
                max-height: calc(max(60vh, 300px));
              }
            `}
          >
            {result ? (
              <>
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
        </>
      }
    />
  );
};
