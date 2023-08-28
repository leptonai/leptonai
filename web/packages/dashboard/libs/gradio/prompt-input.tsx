import { SendAltFilled, StopFilledAlt } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { Button, Col, Input, InputRef, Row, Space } from "antd";
import {
  forwardRef,
  ReactNode,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";

export interface PromptInputRef {
  focus: () => void;
}

export const PromptInput = forwardRef<
  PromptInputRef,
  {
    disabled?: boolean;
    loading: boolean;
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
    submitText?: string;
    submitIcon?: ReactNode;
    onCancel: () => void;
    extra?: ReactNode;
  } & EmotionProps
>(
  (
    {
      disabled = false,
      value,
      onChange,
      loading,
      onCancel,
      onSubmit,
      extra,
      className,
      submitText = "Send",
      submitIcon = <CarbonIcon icon={<SendAltFilled />} />,
    },
    ref
  ) => {
    const inputRef = useRef<InputRef>(null);
    const theme = useAntdTheme();
    const compositionState = useRef(false);

    useImperativeHandle(
      ref,
      () => ({
        focus: () => {
          inputRef.current?.focus();
        },
      }),
      []
    );

    useEffect(() => {
      inputRef.current!.focus({
        cursor: "all",
      });
    }, []);
    return (
      <Row
        onClick={() => inputRef.current?.focus()}
        className={className}
        css={css`
          border: 1px solid ${theme.colorBorder};
          border-radius: ${theme.borderRadius}px;
          background: ${theme.colorBgLayout};
          textarea {
            transition: none;
          }
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
            autoSize={{ minRows: 1, maxRows: 2 }}
            value={value}
            onCompositionStart={() => (compositionState.current = true)}
            onCompositionEnd={() => (compositionState.current = false)}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !compositionState.current
              ) {
                e.preventDefault();
                if (!loading) {
                  onSubmit();
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
            onClick={(e) => e.stopPropagation()}
            css={css`
              margin: ${theme.marginXS}px;
            `}
          >
            {extra}

            {!loading ? (
              <Button
                size="small"
                icon={submitIcon}
                disabled={disabled}
                type="primary"
                onClick={onSubmit}
              >
                {submitText}
              </Button>
            ) : (
              <Button
                size="small"
                icon={<CarbonIcon icon={<StopFilledAlt />} />}
                type="primary"
                onClick={onCancel}
              >
                Stop
              </Button>
            )}
          </Space>
        </Col>
      </Row>
    );
  }
);
