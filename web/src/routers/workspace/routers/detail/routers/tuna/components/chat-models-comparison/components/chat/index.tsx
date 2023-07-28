import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  Button,
  Checkbox,
  Col,
  Input,
  InputRef,
  Row,
  Space,
  Spin,
  Typography,
} from "antd";
import { filter, Subscription, switchMap } from "rxjs";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { CheckboxChangeEvent } from "antd/es/checkbox";
import { css } from "@emotion/react";
import { Scrollable } from "@lepton-dashboard/components/scrollable";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  SendAltFilled,
  StopFilledAlt,
  UserAvatarFilled,
} from "@carbon/icons-react";
import {
  ChatCompletion,
  ChatService,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";

interface ChatProps {
  chat?: ChatCompletion | null;
  disabled?: boolean;
  syncInput: string;
  onInputChanged: (input: string) => void;
  onSend: () => void;
}

export interface ChatRef {
  send: () => void;
}

export const Chat = forwardRef<ChatRef, ChatProps>(
  ({ chat, syncInput, onInputChanged, onSend, disabled }, ref) => {
    const theme = useAntdTheme();
    const [input, setInput] = useState("");
    const [sync, setSync] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [latestUpdate, setLatestUpdate] = useState(0);
    const [loading, setLoading] = useState(false);
    const inputRef = useRef<InputRef | null>(null);
    const subscriptionRef = useRef<Subscription>(Subscription.EMPTY);

    const chat$ = useObservableFromState(chat);

    const messages = useStateFromObservable(
      () =>
        chat$.pipe(
          filter((instance): instance is ChatCompletion => !!instance),
          switchMap((instance) => instance.onMessagesChanged())
        ),
      [],
      {
        next: (value) => {
          setLoading(value.some((item) => item.loading));
        },
        error: () => {
          setLoading(false);
        },
      }
    );

    const send = useCallback(() => {
      if (loading || !input || disabled || !chat) {
        return;
      }
      subscriptionRef.current = chat
        .send(input)
        .subscribe(() => setLatestUpdate(Date.now));
      setInput("");
    }, [input, loading, disabled, chat]);

    const stopGeneration = useCallback(() => {
      subscriptionRef.current.unsubscribe();
    }, []);

    const onSyncChange = useCallback((e: CheckboxChangeEvent) => {
      setSync(e.target.checked);
    }, []);

    const onInnerSend = useCallback(() => {
      send();
      if (sync) {
        onSend();
      }
    }, [onSend, send, sync]);

    const onInnerInputChange = useCallback(
      (input: string) => {
        setInput(input);
        if (sync) {
          onInputChanged(input);
        }
      },
      [onInputChanged, sync]
    );

    useEffect(() => {
      if (sync) {
        setInput(syncInput);
      }
    }, [syncInput, sync]);

    useImperativeHandle(
      ref,
      () => ({
        send: () => {
          if (sync) {
            send();
          }
        },
      }),
      [send, sync]
    );

    // scroll to bottom when messages changed
    useLayoutEffect(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }, [latestUpdate]);

    const focusInput = useCallback(() => {
      inputRef.current?.focus();
    }, []);

    return (
      <div
        css={css`
          border-top: 1px solid ${theme.colorBorderSecondary};
          display: flex;
          flex-direction: column;
          width: 100%;
          height: 100%;
          position: relative;
        `}
      >
        <Scrollable
          scrollableRef={scrollRef}
          margin="8px"
          position={["start", "end"]}
          css={css`
            flex: 1;
            width: 100%;
            background-color: ${theme.colorBgLayout};
          `}
        >
          {messages.map((item, index) => {
            return (
              <div
                key={index}
                css={css`
                  background: ${ChatService.isUserMessage(item)
                    ? theme.colorFillTertiary
                    : item.error
                    ? theme.colorErrorBg
                    : "transparent"};
                  padding: ${theme.paddingSM}px;
                `}
              >
                <Spin spinning={item.loading && !item.responseTime}>
                  {!ChatService.isUserMessage(item) && (
                    <Typography.Text
                      type="secondary"
                      css={css`
                        display: block;
                        font-size: ${theme.fontSizeSM}px;
                        margin-left: 32px;
                      `}
                    >
                      response in{" "}
                      {item.responseTime
                        ? (item.responseTime / 1000).toFixed(2)
                        : "N/A"}
                      s, completion in{" "}
                      {item.completionTime
                        ? (item.completionTime / 1000).toFixed(2)
                        : "N/A"}
                      s
                    </Typography.Text>
                  )}
                  <Space align="start">
                    <div
                      css={css`
                        font-size: 24px;
                        width: 22px;
                        height: 22px;
                        line-height: 22px;
                        text-align: center;
                      `}
                    >
                      {ChatService.isUserMessage(item) ? (
                        <CarbonIcon icon={<UserAvatarFilled />} />
                      ) : (
                        <span
                          css={css`
                            font-size: 20px;
                          `}
                        >
                          AI
                        </span>
                      )}
                    </div>
                    <div
                      css={css`
                        color: ${item.error
                          ? theme.colorError
                          : theme.colorText};
                        white-space: pre-wrap;
                        word-break: break-word;
                        margin-top: 3px;
                      `}
                    >
                      {item.loading && !item.responseTime
                        ? "generating..."
                        : item.error || item.message.content}
                    </div>
                  </Space>
                </Spin>
              </div>
            );
          })}
        </Scrollable>
        <div
          onClick={focusInput}
          css={css`
            flex-shrink: 0;
            position: sticky;
            background: ${theme.colorBgContainer};
            padding: ${theme.paddingSM}px ${theme.paddingXL}px;
            border-top: 1px solid ${theme.colorBorderSecondary};
            bottom: 0;
            left: 0;
            right: 0;
          `}
        >
          <Row
            css={css`
              border: 1px solid ${theme.colorBorder};
              border-radius: ${theme.borderRadiusLG}px;
              transition: border-color 0.18s ease-in-out;
              background: ${theme.colorFillTertiary};
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
                disabled={!chat || disabled}
                ref={inputRef}
                placeholder="Send a message"
                autoSize={{ minRows: 1, maxRows: 5 }}
                value={input}
                onChange={(e) => onInnerInputChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      onInnerSend();
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
                <Checkbox checked={sync} onChange={onSyncChange}>
                  Sync chats
                </Checkbox>
                {!loading ? (
                  <Button
                    icon={<CarbonIcon icon={<SendAltFilled />} />}
                    disabled={!input || !chat || disabled}
                    type="primary"
                    onClick={onInnerSend}
                  >
                    Send
                  </Button>
                ) : (
                  <Button
                    icon={<CarbonIcon icon={<StopFilledAlt />} />}
                    type="primary"
                    onClick={stopGeneration}
                  >
                    Stop
                  </Button>
                )}
              </Space>
            </Col>
          </Row>
        </div>
      </div>
    );
  }
);
