import { FC, PropsWithChildren, useCallback, useMemo, useState } from "react";
import { Button, Checkbox, Col, Form, Input, Row, Typography } from "antd";
import { css } from "@emotion/react";
import { SliderWithNumberInput } from "@lepton-dashboard/routers/playground/components/slider-with-number-input";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Download, Image as ImageIcon } from "@carbon/icons-react";
import { Stopwatch } from "@lepton-dashboard/routers/playground/components/stopwatch";
import { LoadingOutlined } from "@ant-design/icons";
import { CarbonIcon } from "@lepton-dashboard/components/icons";

const Container: FC<PropsWithChildren> = ({ children }) => {
  return (
    <div
      css={css`
        padding: 32px;
        overflow: auto;
        max-height: 100%;
      `}
    >
      {children}
    </div>
  );
};

interface StableDiffusionXlParams {
  prompt: string;
  width: number;
  height: number;
  seed: number;
  num_inference_steps: number;
  use_refiner: boolean;
}

export const StableDiffusionXl: FC = () => {
  const theme = useAntdTheme();
  const [submitting, setSubmitting] = useState(false);
  const [abortController, setAbortController] =
    useState<AbortController | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [altText, setAltText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const playgroundService = useInject(PlaygroundService);

  const backend = useStateFromObservable(
    () => playgroundService.getStableDiffusionXlBackend(),
    null
  );

  const initialValues: StableDiffusionXlParams = useMemo(() => {
    return {
      prompt: "A majestic lion jumping from a big stone at night",
      width: 768, // float (numeric value between 768 and 1024)
      height: 768, // float (numeric value between 768 and 1024)
      seed: 245967316, // float (numeric value between 0 and 2147483647)
      num_inference_steps: 25, // float (numeric value between 1 and 50)
      use_refiner: true,
    };
  }, []);

  const onFinish = useCallback(
    (values: StableDiffusionXlParams) => {
      if (!backend) {
        return;
      }
      if (abortController) {
        abortController.abort();
      }
      const abort = new AbortController();
      setAbortController(abort);
      setSubmitting(true);

      fetch(backend, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
        signal: abort.signal,
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
            setAltText(values.prompt);
          } else {
            setResult(null);
            setError("No result");
          }
        })
        .finally(() => {
          setSubmitting(false);
        });
    },
    [abortController, backend]
  );

  const cancel = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
  }, [abortController]);

  return (
    <Container>
      <Typography.Title>Stable Diffusion XL</Typography.Title>
      <Row gutter={16}>
        <Col span={24} xl={9}>
          <Form
            initialValues={initialValues}
            onFinish={onFinish}
            disabled={!backend}
          >
            <div
              css={css`
                position: relative;
              `}
            >
              <Form.Item name="prompt">
                <Input.TextArea
                  css={css`
                    padding-right: 110px;
                  `}
                  autoSize={{
                    minRows: 2,
                    maxRows: 6,
                  }}
                />
              </Form.Item>
              <div
                css={css`
                  position: absolute;
                  right: 8px;
                  bottom: 11px;
                  width: 100px;
                  text-align: center;
                  button {
                    width: 100%;
                  }
                `}
              >
                {submitting ? (
                  <Button
                    htmlType="button"
                    icon={<LoadingOutlined />}
                    onClick={(e) => {
                      // htmlType="button" seems not working, so preventDefault manually
                      e.preventDefault();
                      cancel();
                    }}
                  >
                    Cancel
                  </Button>
                ) : (
                  <Button type="primary" htmlType="submit">
                    Generate
                  </Button>
                )}
              </div>
            </div>
            <Form.Item name="width" label="Width">
              <SliderWithNumberInput min={768} max={1024} integer />
            </Form.Item>
            <Form.Item name="height" label="Height">
              <SliderWithNumberInput min={768} max={1024} integer />
            </Form.Item>
            <Form.Item name="seed" label="Seed">
              <SliderWithNumberInput min={0} max={2147483647} integer />
            </Form.Item>
            <Form.Item name="num_inference_steps" label="Steps">
              <SliderWithNumberInput min={1} max={50} integer />
            </Form.Item>
            <Form.Item
              name="use_refiner"
              valuePropName="checked"
              label="Use Refiner"
            >
              <Checkbox />
            </Form.Item>
          </Form>
        </Col>
        <Col span={24} xl={15}>
          <div
            css={css`
              position: relative;
              border: 1px solid ${theme.colorBorder};
              background: ${theme.colorBgContainer};
              border-radius: ${theme.borderRadius};
              padding: 16px;
              min-height: 350px;
              display: flex;
              justify-content: center;
              align-items: center;
              img {
                width: auto;
                max-height: 75vh;
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
                  `}
                  download
                  href={result}
                  target="_blank"
                  type="text"
                  size="small"
                  icon={<CarbonIcon icon={<Download />} />}
                />
                <img src={result} alt={altText || ""} />
              </>
            ) : error ? (
              <Typography.Text type="danger">{error}</Typography.Text>
            ) : (
              <div
                css={css`
                  color: ${theme.colorTextSecondary};
                `}
              >
                {submitting ? (
                  <Typography.Text type="secondary">
                    Generating... (<Stopwatch start />)
                  </Typography.Text>
                ) : (
                  <ImageIcon size={32} />
                )}
              </div>
            )}
          </div>
        </Col>
      </Row>
    </Container>
  );
};
