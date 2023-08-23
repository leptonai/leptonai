import { ChatBot } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ScrollableRef } from "@lepton-dashboard/components/scrollable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Container } from "@lepton-dashboard/routers/playground/components/container";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { ChatMessages } from "@lepton-libs/gradio/chat-messages";
import { ChatOptions } from "@lepton-libs/gradio/chat-options";
import {
  ChatCompletion,
  ChatOption,
  ChatService,
} from "@lepton-libs/gradio/chat.service";
import { PromptInput } from "@lepton-libs/gradio/prompt-input";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import pathJoin from "@lepton-libs/url/path-join";
import { FC, useCallback, useRef, useState } from "react";
import { filter, map, Subscription, switchMap, throttleTime } from "rxjs";
import { TitleService } from "@lepton-dashboard/services/title.service";

export const Llama2: FC = () => {
  const titleService = useInject(TitleService);
  titleService.setTitle("🦙 Llama2", true);
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
  const playgroundService = useInject(PlaygroundService);
  const chat = useStateFromObservable(
    () =>
      playgroundService.getLlama2Backend().pipe(
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
  return (
    <Container
      loading={!chat}
      icon={<CarbonIcon icon={<ChatBot />} />}
      title="Llama2"
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
