import { ChatBot } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ScrollableRef } from "@lepton-dashboard/components/scrollable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Container } from "@lepton-dashboard/routers/playground/components/container";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { APICodeTemplate } from "@lepton-libs/gradio/api-code-template";
import { ChatMessages } from "@lepton-libs/gradio/chat-messages";
import { ChatOptions } from "@lepton-libs/gradio/chat-options";
import {
  ChatCompletion,
  ChatOption,
  ChatService,
} from "@lepton-libs/gradio/chat.service";
import { PromptInput, PromptInputRef } from "@lepton-libs/gradio/prompt-input";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import pathJoin from "@lepton-libs/url/path-join";
import { FC, useCallback, useMemo, useRef, useState } from "react";
import { filter, map, Subscription, switchMap, tap, throttleTime } from "rxjs";
import { MetaService } from "@lepton-dashboard/services/meta.service";
import { Dropdown, Space } from "antd";
import { DownOutlined } from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { Api } from "@lepton-dashboard/routers/playground/components/api";

const modelMap = {
  "llama-2-7b": {
    name: "Llama-2-7b",
  },
  "llama-2-70b": {
    name: "Llama-2-70b",
  },
} as const;

type Model = keyof typeof modelMap;

const DEFAULT_MODEL: Model = "llama-2-7b";

const getValidModel = (model: string): Model => {
  if (model in modelMap) {
    return model as Model;
  } else {
    return DEFAULT_MODEL;
  }
};
export const Llama2: FC = () => {
  const metaService = useInject(MetaService);
  metaService.setTitle("🦙 Llama2", true);
  metaService.setURLPath();
  const inputRef = useRef<PromptInputRef>(null);
  const [params] = useSearchParams();
  const modelFromURL = getValidModel(params.get("model") || "");
  const [model, setModel] = useState<Model>(modelFromURL);
  const [option, setOption] = useState<ChatOption>({
    max_tokens: 512,
    top_p: 0.8,
    temperature: 0.5,
  });
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("Hi, how are you");
  const subscriptionRef = useRef<Subscription>(Subscription.EMPTY);
  const chatService = useInject(ChatService);
  const theme = useAntdTheme();
  const [url, setUrl] = useState("");
  const playgroundService = useInject(PlaygroundService);
  const model$ = useObservableFromState(model);
  const chat = useStateFromObservable(
    () =>
      model$.pipe(
        switchMap((model) => {
          if (model === "llama-2-7b") {
            return playgroundService.getLlamaBackend();
          } else {
            return playgroundService.getLlama70bBackend();
          }
        }),
        tap((url) => setUrl(url)),
        map((url) =>
          chatService.createChat({
            api_url: pathJoin(url, "chat/completions"),
          })
        )
      ),
    null
  );
  const chat$ = useObservableFromState(chat);
  const scrollRef = useRef<ScrollableRef>(null);
  const submit = useCallback(() => {
    if (loading || !prompt || !chat) {
      return;
    }
    subscriptionRef.current = chat
      .send(prompt, option)
      .pipe(throttleTime(100))
      .subscribe(() => scrollRef?.current?.scrollToBottom());
    setPrompt("");
  }, [loading, prompt, chat, option]);

  const messages = useStateFromObservable(
    () =>
      chat$.pipe(
        filter((instance): instance is ChatCompletion => !!instance),
        switchMap((instance) => instance.onMessagesChanged())
      ),
    [],
    {
      next: (value) => {
        const loading = value.some((item) => item.loading);
        setLoading(loading);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  const modelMenu = useMemo(() => {
    return {
      items: (Object.keys(modelMap) as Model[]).map((key) => ({
        key,
        label: modelMap[key].name,
        title: modelMap[key].name,
      })),
      onClick: ({ key }: { key: string }) => {
        setModel(key as Model);
        // focus input
        inputRef.current?.focus();
        // set query params
        const url = new URL(window.location.href);
        url.searchParams.set("model", key);
        window.history.replaceState({}, "", url.toString());
      },
    };
  }, []);

  const codes = Object.entries(
    APICodeTemplate.chat(url, "YOUR_EMAIL_ADDRESS")
  ).map(([language, code]) => ({ language, code }));

  return (
    <Container
      loading={!chat}
      icon={<CarbonIcon icon={<ChatBot />} />}
      extra={<Api name="Llama2" codes={codes} />}
      title={
        <>
          <Dropdown menu={modelMenu} trigger={["click"]}>
            <Space
              css={css`
                cursor: pointer;
              `}
            >
              <span>{modelMap[model].name}</span>
              <DownOutlined />
            </Space>
          </Dropdown>
        </>
      }
      content={
        <div
          css={css`
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            position: relative;
          `}
        >
          <div
            css={css`
              border: 1px solid ${theme.colorBorder};
              flex: 1 1 auto;
              min-height: 300px;
              overflow: hidden;
              position: relative;
              display: flex;
              margin-bottom: 12px;
              border-radius: ${theme.borderRadius}px;
            `}
          >
            <div
              css={css`
                position: absolute;
                inset: 0;
                display: flex;
                flex-direction: column;
              `}
            >
              <ChatMessages messages={messages} ref={scrollRef} />
            </div>
          </div>
          <PromptInput
            css={css`
              flex: 0 1 auto;
            `}
            ref={inputRef}
            loading={loading}
            value={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            onCancel={() => subscriptionRef.current.unsubscribe()}
          />
        </div>
      }
      option={
        <ChatOptions chatOption={option} onChatOptionChanged={setOption} />
      }
    />
  );
};
