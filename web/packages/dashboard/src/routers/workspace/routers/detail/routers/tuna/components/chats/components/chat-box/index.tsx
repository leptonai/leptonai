import { ScrollableRef } from "@lepton/ui/components/scrollable";
import { ChatInput } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats/components/chat-input";
import { ChatMessages } from "@lepton/playground/components/chat/chat-messages";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { filter, Subscription, switchMap, throttleTime } from "rxjs";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { css } from "@emotion/react";
import { ChatCompletion, ChatOption } from "@lepton/playground/shared/chat";

interface ChatProps {
  chat?: ChatCompletion | null;
  chatOption: ChatOption;
  disabled?: boolean;
  syncInput: string;
  onInputChanged: (input: string) => void;
  onLoadingChanged: (loading: boolean) => void;
  onSend: () => void;
}

export interface ChatRef {
  send: () => void;
}

export const ChatBox = forwardRef<ChatRef, ChatProps>(
  (
    {
      chat,
      syncInput,
      chatOption,
      onInputChanged,
      onLoadingChanged,
      onSend,
      disabled,
    },
    ref
  ) => {
    const [input, setInput] = useState("");
    const [sync, setSync] = useState(true);
    const scrollRef = useRef<ScrollableRef>(null);
    const [loading, setLoading] = useState(false);
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
          const loading = value.some((item) => item.loading);
          setLoading(loading);
          onLoadingChanged(loading);
        },
        error: () => {
          setLoading(false);
          onLoadingChanged(false);
        },
      }
    );

    const send = useCallback(() => {
      if (loading || !input || disabled || !chat) {
        return;
      }
      subscriptionRef.current = chat
        .send(input, chatOption)
        .pipe(throttleTime(100))
        .subscribe(() => scrollRef?.current?.scrollToBottom());
      setInput("");
    }, [loading, input, disabled, chat, chatOption]);

    const onInnerSend = useCallback(() => {
      send();
      if (sync && onSend) {
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

    return (
      <div
        css={css`
          display: flex;
          flex-direction: column;
          width: 100%;
          height: 100%;
          position: relative;
        `}
      >
        <ChatMessages messages={messages} ref={scrollRef} />
        <ChatInput
          disabled={disabled || !chat}
          loading={loading}
          sync={sync}
          onSyncChanged={setSync}
          input={input}
          onInputChanged={onInnerInputChange}
          onSend={onInnerSend}
          onStopGeneration={() => subscriptionRef.current.unsubscribe()}
        />
      </div>
    );
  }
);
