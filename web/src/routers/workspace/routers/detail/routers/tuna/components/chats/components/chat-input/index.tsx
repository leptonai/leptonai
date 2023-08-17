import { SendAltFilled, StopFilledAlt } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Button, Checkbox, Col, Input, InputRef, Row, Space } from "antd";
import { FC, useRef } from "react";

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
  const inputRef = useRef<InputRef | null>(null);
  return (
    <div
      onClick={() => inputRef.current?.focus()}
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
      <Row
        css={css`
          border: 1px solid ${theme.colorBorder};
          border-radius: ${theme.borderRadius}px;
          background: ${theme.colorBgLayout};
          transition: border-color 0.18s ease-in-out;
          max-width: 800px;
          margin: 0 auto;
          &:hover,
          &:focus-within {
            border-color: ${theme.colorPrimaryBorderHover};
          }
          textarea {
            background: transparent;
            &:focus,
            &:hover {
              background: transparent;
            }
          }
          .ant-btn-primary:disabled {
            background: ${theme.colorBgContainer};
          }
        `}
      >
        <Col span={24}>
          <Input.TextArea
            bordered={false}
            disabled={disabled}
            ref={inputRef}
            placeholder="Send a message"
            autoSize={{ minRows: 1, maxRows: 5 }}
            value={input}
            autoFocus
            onChange={(e) => onInputChanged(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                if (!e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }
            }}
          />
        </Col>
        <Col
          span={24}
          css={css`
            display: flex;
            flex-direction: row-reverse;
          `}
        >
          <Space
            css={css`
              margin: ${theme.marginXS}px;
            `}
          >
            <Checkbox
              checked={sync}
              onChange={(e) => onSyncChanged(e.target.checked)}
            >
              Sync chats
            </Checkbox>
            {!loading ? (
              <Button
                icon={<CarbonIcon icon={<SendAltFilled />} />}
                disabled={!input || disabled}
                type="primary"
                onClick={onSend}
              >
                Send
              </Button>
            ) : (
              <Button
                icon={<CarbonIcon icon={<StopFilledAlt />} />}
                type="primary"
                onClick={onStopGeneration}
              >
                Stop
              </Button>
            )}
          </Space>
        </Col>
      </Row>
    </div>
  );
};
