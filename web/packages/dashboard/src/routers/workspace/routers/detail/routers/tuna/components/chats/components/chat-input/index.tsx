import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { PromptInput } from "@lepton/playground/components/prompt-input";
import { Checkbox } from "antd";
import { FC } from "react";

export const ChatInput: FC<{
  disabled: boolean;
  loading: boolean;
  sync: boolean;
  onSyncChanged: (sync: boolean) => void;
  input: string;
  onInputChanged: (input: string) => void;
  onSend: () => void;
  onStopGeneration: () => void;
}> = ({
  loading,
  disabled,
  input,
  onInputChanged,
  sync,
  onSyncChanged,
  onSend,
  onStopGeneration,
}) => {
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        flex-shrink: 0;
        position: sticky;
        background: ${theme.colorBgContainer};
        padding: ${theme.paddingSM}px ${theme.paddingXL}px;
        border-top: 1px solid ${theme.colorBorder};
        bottom: 0;
        left: 0;
        right: 0;
      `}
    >
      <PromptInput
        css={css`
          max-width: 800px;
          margin: 0 auto;
        `}
        loading={loading}
        value={input}
        disabled={disabled}
        onChange={onInputChanged}
        onSubmit={onSend}
        onCancel={onStopGeneration}
        extra={
          <Checkbox
            checked={sync}
            onChange={(e) => onSyncChanged(e.target.checked)}
          >
            Sync chats
          </Checkbox>
        }
      />
    </div>
  );
};
