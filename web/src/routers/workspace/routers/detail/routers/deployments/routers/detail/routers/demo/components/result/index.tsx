import { FC, useMemo } from "react";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Typography } from "antd";
import {
  LanguageSupports,
  SyntaxHighlight,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/components/syntax-highlight";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";

// https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
export type SupportedContentTypes =
  | "application/json"
  | "text/plain"
  | "audio/wav"
  | "audio/webm"
  | "audio/mpeg"
  | "image/png"
  | "image/gif"
  | "image/jpeg"
  | "image/svg+xml"
  | "image/webp"
  | "image/bmp";

export type ContentDisplayMap = {
  [key in SupportedContentTypes]?: ResultDisplay;
};

export interface DEMOResultPayload {
  payload: string | SafeAny | Blob;
  contentType: SupportedContentTypes;
}

export interface DEMOResultError {
  error: string;
}

export type DEMOResult = DEMOResultPayload | DEMOResultError;
export type ResultDisplay = FC<{
  content: SafeAny;
  mime: SupportedContentTypes;
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
  if (/^audio\/wav/i.test(contentType)) {
    return "audio/wav";
  }
  if (/^image\/png/i.test(contentType)) {
    return "image/png";
  }
  return "text/plain";
};

const ResultTextDisplay: ResultDisplay = ({ content }) => {
  return <>{content}</>;
};

const ResultJSONDisplay: ResultDisplay = ({ content }) => {
  return (
    <div
      css={css`
        pre {
          margin: 0;
          overflow: auto;
        }
      `}
    >
      <SyntaxHighlight
        code={JSON.stringify(content, null, 2)}
        language={LanguageSupports.JSON}
      />
    </div>
  );
};

const ErrorTextDisplay: ResultDisplay = ({ content }) => {
  return <Typography.Text type="danger">{content}</Typography.Text>;
};

const DisplayMap: ContentDisplayMap = {
  "application/json": ResultJSONDisplay,
  "text/plain": ResultTextDisplay,
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
    <div
      css={css`
        margin: 0;
        background: ${theme.colorBgLayout};
        height: 100%;
        border: 1px solid ${theme.colorBorder};
        border-radius: ${theme.borderRadius}px;
        word-break: break-word;
        white-space: pre-wrap;
        color: ${theme.colorText};
        padding: 32px;
      `}
    >
      {displayResult}
    </div>
  );
};
