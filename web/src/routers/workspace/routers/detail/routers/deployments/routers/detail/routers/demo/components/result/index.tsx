import { FC, useMemo } from "react";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Space, Typography } from "antd";
import { LanguageSupports, CodeBlock } from "../../../../components/code-block";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

// https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
export type SupportedContentTypes =
  | "application/json"
  | "text/plain"
  | "image/*"
  | "audio/*"
  | "video/*";

export type ContentDisplayMap = {
  [key in SupportedContentTypes]?: ResultDisplay;
};

export interface DEMOResultPayload {
  payload: string | SafeAny | Blob;
  contentType: SupportedContentTypes;
  executionTime?: number;
}

export interface DEMOResultError {
  error: string;
  executionTime?: number;
}

export type DEMOResult = DEMOResultPayload | DEMOResultError;
export type ResultDisplay = FC<{
  content: SafeAny;
  mime?: SupportedContentTypes;
}>;

const isDEMOResultPayload = (
  result: DEMOResult
): result is DEMOResultPayload => {
  return (result as DEMOResultPayload).payload !== undefined;
};

const normalizeContentType = (contentType?: string): SupportedContentTypes => {
  if (!contentType) {
    return "text/plain";
  }
  if (/^application\/json/i.test(contentType)) {
    return "application/json";
  }
  if (/^image\//i.test(contentType)) {
    return "image/*";
  }
  if (/^audio\//i.test(contentType)) {
    return "audio/*";
  }
  if (/^video\//i.test(contentType)) {
    return "video/*";
  }

  return "text/plain";
};

const canStringify = (content: SafeAny): content is string => {
  return typeof content?.toString === "function";
};

const isBlob = (content: SafeAny): content is Blob => {
  return content instanceof Blob;
};

const ErrorTextDisplay: ResultDisplay = ({ content }) => {
  let errorText = "";
  if (canStringify(content)) {
    errorText = content.toString();
  } else if (content instanceof Error) {
    errorText = content.message;
  } else {
    errorText = "Unknown error";
  }
  return (
    <Typography.Text
      css={css`
        width: 100%;
      `}
      type="danger"
    >
      {errorText}
    </Typography.Text>
  );
};

const PlainTextDisplay: ResultDisplay = ({ content }) => {
  if (canStringify(content)) {
    return (
      <Typography.Text
        css={css`
          width: 100%;
        `}
      >
        {content.toString()}
      </Typography.Text>
    );
  } else {
    return <ErrorTextDisplay content={content} mime="text/plain" />;
  }
};

const JSONDisplay: ResultDisplay = ({ content }) => {
  try {
    const code = JSON.stringify(content, null, 2);
    return (
      <div
        css={css`
          width: 100%;
          pre {
            margin: 0;
            overflow: auto;
          }
        `}
      >
        <CodeBlock code={code} language={LanguageSupports.JSON} copyable />
      </div>
    );
  } catch (e) {
    return <ErrorTextDisplay content={e} />;
  }
};

const ImageDisplay: ResultDisplay = ({ content }) => {
  if (isBlob(content)) {
    try {
      return (
        <img
          src={URL.createObjectURL(content)}
          css={css`
            max-width: 100%;
            max-height: 100%;
          `}
        />
      );
    } catch (e) {
      return <ErrorTextDisplay content={e} />;
    }
  } else {
    return (
      <ErrorTextDisplay
        content="The result is not a valid binary, cannot display as an image."
        mime="text/plain"
      />
    );
  }
};

const AudioDisplay: ResultDisplay = ({ content }) => {
  if (isBlob(content)) {
    try {
      return (
        <audio controls>
          <source src={URL.createObjectURL(content)} />
        </audio>
      );
    } catch (e) {
      return <ErrorTextDisplay content={e} />;
    }
  } else {
    return (
      <ErrorTextDisplay
        content="The result is not a valid binary, cannot play as an audio."
        mime="text/plain"
      />
    );
  }
};

export const VideoDisplay: ResultDisplay = ({ content }) => {
  if (isBlob(content)) {
    try {
      return (
        <video controls width="100%">
          <source src={URL.createObjectURL(content)} />
        </video>
      );
    } catch (e) {
      return <ErrorTextDisplay content={e} />;
    }
  } else {
    return (
      <ErrorTextDisplay
        content="The result is not a valid binary, cannot play as a video."
        mime="text/plain"
      />
    );
  }
};

const DisplayMap: ContentDisplayMap = {
  "application/json": JSONDisplay,
  "text/plain": PlainTextDisplay,
  "image/*": ImageDisplay,
  "audio/*": AudioDisplay,
  "video/*": VideoDisplay,
};

export const Result: FC<{ result: DEMOResult }> = ({ result }) => {
  const displayResult = useMemo(() => {
    if (isDEMOResultPayload(result)) {
      const contentType = normalizeContentType(result.contentType);
      const Display = DisplayMap[contentType];
      const content = result.payload;
      if (Display) {
        return <Display content={content} mime={contentType} />;
      } else {
        return (
          <ErrorTextDisplay
            mime="text/plain"
            content={`content type ${contentType} not supported`}
          />
        );
      }
    } else {
      return <ErrorTextDisplay mime="text/plain" content={result.error} />;
    }
  }, [result]);
  const theme = useAntdTheme();

  return (
    <Space
      direction="vertical"
      css={css`
        width: 100%;
      `}
    >
      <div
        css={css`
          margin: 0;
          height: auto;
          display: flex;
          justify-content: center;
          align-items: center;
          background: ${theme.colorBgLayout};
          border: 1px solid ${theme.colorBorder};
          border-radius: ${theme.borderRadius}px;
          word-break: break-word;
          white-space: pre-wrap;
          color: ${theme.colorText};
          padding: 16px;
        `}
      >
        {displayResult}
      </div>
      <Space>
        {result.executionTime && (
          <Typography.Text type="secondary">
            Output in {(result.executionTime / 1000).toFixed(2)} seconds
          </Typography.Text>
        )}
      </Space>
    </Space>
  );
};
