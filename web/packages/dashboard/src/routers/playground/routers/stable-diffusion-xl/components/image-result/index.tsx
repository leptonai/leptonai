import { LoadingOutlined } from "@ant-design/icons";
import { Download, Image } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Stopwatch } from "@lepton-dashboard/routers/playground/routers/stable-diffusion-xl/components/stopwatch";
import { Button, Image as AntdImage, Spin, Typography } from "antd";
import { cloneElement, FC, ReactElement } from "react";

export const ImageResult: FC<{
  result: string | null;
  prompt: string;
  error: string | null;
  hasResponse: boolean;
  loading: boolean;
}> = ({ result, prompt, loading, hasResponse, error }) => {
  const theme = useAntdTheme();
  if (result) {
    return (
      <>
        <div
          css={css`
            position: absolute;
            inset: 0;
            backdrop-filter: blur(100px);
            overflow: hidden;
            border-radius: ${theme.borderRadius}px;
          `}
        />
        <Button
          css={css`
            position: absolute;
            top: 8px;
            right: 8px;
            z-index: 1;
            opacity: 0.5;
          `}
          download
          href={result}
          target="_blank"
          size="small"
          icon={<CarbonIcon icon={<Download />} />}
        />
        <AntdImage
          height="100%"
          preview={{
            imageRender: (node, { transform }) => {
              const scale = transform.scale * 1.5;
              const style = {
                transform: `translate3d(${transform.x}px, ${
                  transform.y
                }px, 0) scale3d(${transform.flipX ? "-" : ""}${scale}, ${
                  transform.flipY ? "-" : ""
                }${scale}, 1) rotate(${transform.rotate}deg)`,
              };
              return cloneElement(node as ReactElement, {
                style,
              });
            },
          }}
          width="auto"
          alt={prompt || ""}
          src={result}
        />
      </>
    );
  }
  return (
    <div
      css={css`
        border: 1px solid ${theme.colorBorder};
        overflow: hidden;
        color: ${theme.colorTextSecondary};
        border-radius: ${theme.borderRadius}px;
        background: ${theme.colorBgLayout};
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
      `}
    >
      {error ? (
        <Typography.Text type="danger">{error}</Typography.Text>
      ) : loading ? (
        <>
          <div
            css={css`
              margin-bottom: 6px;
            `}
          >
            <Spin indicator={<LoadingOutlined />} />
          </div>
          {hasResponse ? (
            <Typography.Text type="secondary">Rendering...</Typography.Text>
          ) : (
            <Typography.Text type="secondary">
              Generating... (<Stopwatch start />)
            </Typography.Text>
          )}
        </>
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
  );
};
