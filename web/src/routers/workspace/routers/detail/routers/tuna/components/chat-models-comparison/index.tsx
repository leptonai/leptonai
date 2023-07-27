import {
  FC,
  forwardRef,
  PropsWithChildren,
  ReactNode,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Button,
  Checkbox,
  Col,
  Input,
  InputRef,
  Row,
  Select,
  Space,
  Spin,
  Typography,
} from "antd";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  BehaviorSubject,
  map,
  Observable,
  Subscription,
  switchMap,
} from "rxjs";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  ChatGPTMessage,
  openAIStream,
  OpenAIStreamOption,
} from "@lepton-libs/open-ai-like/open-ai-stream";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  Code,
  SendAltFilled,
  StopFilledAlt,
  UserAvatarFilled,
} from "@carbon/icons-react";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { CheckboxChangeEvent } from "antd/es/checkbox";
import { Scrollable } from "@lepton-dashboard/components/scrollable";
import { useInject } from "@lepton-libs/di";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { useParams } from "react-router-dom";
import { ApiModal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/api-modal";
import pathJoin from "@lepton-libs/url/path-join";

export interface ChatModelsComparisonProps {
  name: string;
}

export interface ChatMessageItem {
  loading?: boolean;
  error?: string;
  responseTime?: number;
  completionTime?: number;
  message: ChatGPTMessage;
}

const isUserMessage = (message: ChatMessageItem): boolean => {
  return message.message.role === "user";
};

class Chat {
  private messages$ = new BehaviorSubject<ChatMessageItem[]>([]);
  constructor(private option: OpenAIStreamOption) {}

  onMessagesChanged(): Observable<ChatMessageItem[]> {
    return this.messages$.asObservable();
  }

  send(content: string): Observable<string> {
    const userItem: ChatMessageItem = {
      message: {
        role: "user",
        content,
      },
      loading: false,
    };
    this.push(userItem);

    const messages = this.messages$.value
      .filter((item) => !item.loading && !item.error)
      .map((item) => item.message);

    const aiItem = this.pushLoading();

    return new Observable((subscriber) => {
      const abortController = new AbortController();
      const now = Date.now();
      openAIStream(
        {
          model: "gpt-3.5-turbo",
          messages,
          stream: true,
        },
        this.option,
        abortController
      )
        .then((stream$) => {
          aiItem.responseTime = Date.now() - now;
          this.refresh();
          stream$.subscribe({
            next: (chunkOfMessages) => {
              aiItem.message.content += chunkOfMessages;
              subscriber.next(chunkOfMessages);
              this.refresh();
            },
            complete: () => {
              aiItem.completionTime = Date.now() - now;
              this.refresh();
              aiItem.loading = false;
              subscriber.next("[DONE]");
              subscriber.complete();
            },
            error: (e) => {
              aiItem.completionTime = Date.now() - now;
              aiItem.loading = false;
              if (abortController.signal.aborted) {
                this.refresh();
                return;
              }
              if (typeof e === "string") {
                aiItem.error = e;
              } else if (e instanceof Error) {
                aiItem.error = e.message;
              } else {
                aiItem.error = e?.error?.message || "Something went wrong";
              }
              this.refresh();
              subscriber.error(e);
            },
          });
        })
        .catch((e) => {
          aiItem.loading = false;
          if (typeof e === "string") {
            aiItem.error = e;
          } else if (e instanceof Error) {
            aiItem.error = e.message;
          } else {
            aiItem.error = "Something went wrong";
          }
          this.refresh();
          subscriber.error(e);
        });
      return () => {
        abortController.abort();
        if (!aiItem.responseTime && !aiItem.error) {
          this.remove(userItem);
          this.remove(aiItem);
        } else {
          aiItem.loading = false;
          this.refresh();
        }
      };
    });
  }

  private refresh(): void {
    this.messages$.next([...this.messages$.value]);
  }

  private remove(item: ChatMessageItem): void {
    this.messages$.next(this.messages$.value.filter((i) => i !== item));
  }

  private push(item: ChatMessageItem): void {
    this.messages$.next([...this.messages$.value, item]);
  }

  private pushLoading(): ChatMessageItem {
    const item: ChatMessageItem = {
      loading: true,
      message: {
        role: "assistant",
        content: "",
      },
    };
    this.push(item);
    return item;
  }
}

interface ChatBoxProps {
  apiUrl?: string;
  disabled?: boolean;
  apiKey?: string;
  syncInput: string;
  onInputChanged: (input: string) => void;
  onSend: () => void;
}

interface ChatBoxRef {
  send: () => void;
}

const ChatBox = forwardRef<ChatBoxRef, ChatBoxProps>(
  ({ apiUrl, apiKey, syncInput, onInputChanged, onSend, disabled }, ref) => {
    const theme = useAntdTheme();
    const [input, setInput] = useState("");
    const [sync, setSync] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [latestChunk, setLatestChunk] = useState("");
    const [loading, setLoading] = useState(false);
    const inputRef = useRef<InputRef | null>(null);
    const subscriptionRef = useRef<Subscription>(Subscription.EMPTY);

    const chat = useMemo(
      () =>
        new Chat({
          api_url: pathJoin(apiUrl || "", "chat/completions"),
          api_key: apiKey,
        }),
      [apiUrl, apiKey]
    );
    const chat$ = useObservableFromState(chat);

    const messages = useStateFromObservable(
      () => chat$.pipe(switchMap((instance) => instance.onMessagesChanged())),
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
      if (loading || !input || disabled || !apiUrl) {
        return;
      }
      subscriptionRef.current = chat.send(input).subscribe(setLatestChunk);
      setInput("");
    }, [chat, input, loading, disabled, apiUrl]);

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
    }, [latestChunk]);

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
                  background: ${isUserMessage(item)
                    ? theme.colorFillTertiary
                    : item.error
                    ? theme.colorErrorBg
                    : "transparent"};
                  padding: ${theme.paddingSM}px;
                `}
              >
                <Spin spinning={item.loading && !item.responseTime}>
                  {!isUserMessage(item) && (
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
                      {isUserMessage(item) ? (
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
                disabled={!apiUrl || disabled}
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
                    disabled={!input || !apiUrl || disabled}
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

export const ChatPart: FC<PropsWithChildren & { header: ReactNode }> = ({
  header,
  children,
}) => {
  const theme = useAntdTheme();
  return (
    <div
      css={css`
        display: flex;
        flex-direction: column;
        height: 100%;
        width: 100%;
      `}
    >
      <div
        css={css`
          flex: 0;
          border-bottom: 1px solid ${theme.colorBorder};
        `}
      >
        {header}
      </div>
      <div
        css={css`
          flex: 1;
          overflow: hidden;
        `}
      >
        {children}
      </div>
    </div>
  );
};

interface ModelOption {
  name: string;
  apiOption: OpenAIStreamOption;
}

const benchmarkModel: ModelOption = {
  name: "llama2",
  apiOption: {
    api_url: "https://llama2.llm.lepton.run/api/v1",
  },
};

const ChatHeader: FC<{
  modelName: string;
  onModelChange: (option: ModelOption) => void;
}> = ({ modelName, onModelChange }) => {
  const theme = useAntdTheme();
  const tunaService = useInject(TunaService);
  const [value, setValue] = useState(benchmarkModel.name);
  const [loading, setLoading] = useState(true);
  const models = useStateFromObservable(
    () =>
      tunaService.listInferences().pipe(
        map((inference) => {
          return [
            benchmarkModel,
            ...inference
              .filter((i) => i.status?.api_endpoint)
              .map((i) => {
                return {
                  name: i.metadata.name,
                  apiOption: {
                    api_url: i.status?.api_endpoint,
                  },
                };
              }),
          ] as ModelOption[];
        })
      ),
    [benchmarkModel],
    {
      next: () => {
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  const onChange = useCallback(
    (value: string) => {
      const model = models.find((m) => m.name === value);
      if (model) {
        setValue(value);
        onModelChange(model);
      }
    },
    [models, onModelChange]
  );

  useEffect(() => {
    if (loading) {
      return;
    }
    const model = models.find((m) => m.name === modelName);
    if (model) {
      onChange(model.name);
    } else {
      onChange(benchmarkModel.name);
    }
  }, [modelName, models, onChange, loading]);

  const model = useMemo(() => {
    return models.find((m) => m.name === value);
  }, [models, value]);

  return (
    <div
      css={css`
        padding: ${theme.paddingSM}px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      `}
    >
      <div>
        <Select
          disabled={loading}
          loading={loading}
          css={css`
            width: 256px;
          `}
          value={value}
          onChange={onChange}
          options={models.map((i) => ({ label: i.name, value: i.name }))}
        />
      </div>
      <div>
        <Space>
          <ApiModal
            disabled={loading || !model}
            icon={<CarbonIcon icon={<Code />} />}
            apiUrl={model?.apiOption.api_url || ""}
            apiKey={model?.apiOption.api_key}
            name={model?.name || ""}
          />
        </Space>
      </div>
    </div>
  );
};

export const ChatModelsComparison: FC<ChatModelsComparisonProps> = () => {
  const { name } = useParams<{ name: string }>();
  const theme = useAntdTheme();
  const [input, setInput] = useState("");
  const [modelA, setModelA] = useState<ModelOption | null>(benchmarkModel);
  const [modelB, setModelB] = useState<ModelOption | null>(null);
  const chatRefMap = useRef({
    modelA: null as null | ChatBoxRef,
    modelB: null as null | ChatBoxRef,
  });

  const onSendFrom = useCallback((key: string) => {
    const map = chatRefMap.current || {};
    (Object.keys(map) as (keyof typeof map)[])
      .filter((k) => k !== key)
      .forEach((k) => {
        map[k]?.send();
      });
  }, []);

  return (
    <Row
      css={css`
        height: calc(100vh - 225px);
      `}
    >
      <Col
        span={24}
        md={12}
        css={css`
          border-right: 1px solid ${theme.colorBorder};
          height: 100%;
          @media (max-width: 768px) {
            border-right: none;
            border-bottom: 1px solid ${theme.colorBorder};
            height: 50%;
          }
        `}
      >
        <ChatPart
          header={
            <ChatHeader
              modelName={benchmarkModel.name}
              onModelChange={setModelA}
            />
          }
        >
          <ChatBox
            disabled={!modelA}
            ref={(ref) => {
              chatRefMap.current["modelA"] = ref;
            }}
            apiUrl={modelA?.apiOption.api_url}
            apiKey={modelA?.apiOption.api_key}
            syncInput={input}
            onInputChanged={setInput}
            onSend={() => onSendFrom("modelA")}
          />
        </ChatPart>
      </Col>
      <Col
        span={24}
        md={12}
        css={css`
          height: 100%;
          @media (max-width: 768px) {
            height: 50%;
          }
        `}
      >
        <ChatPart
          header={
            <ChatHeader
              modelName={name || benchmarkModel.name}
              onModelChange={setModelB}
            />
          }
        >
          <ChatBox
            ref={(ref) => {
              chatRefMap.current["modelB"] = ref;
            }}
            disabled={!modelB}
            apiUrl={modelB?.apiOption.api_url}
            apiKey={modelB?.apiOption.api_key}
            syncInput={input}
            onInputChanged={setInput}
            onSend={() => onSendFrom("modelB")}
          />
        </ChatPart>
      </Col>
    </Row>
  );
};
