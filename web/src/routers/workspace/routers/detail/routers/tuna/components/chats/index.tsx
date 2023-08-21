import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Chat } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats/components/chat";
import { ChatRef } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats/components/chat-box";
import { ModelOption } from "@lepton-libs/gradio/chat.service";
import { Empty } from "antd";
import { FC, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

export const Chats: FC<{ baseName?: string; models: ModelOption[] }> = ({
  baseName,
  models,
}) => {
  const theme = useAntdTheme();
  const baseModel = models.find((m) => m.name === baseName);
  const llm2Model = models.find((m) => m.name === "llama2")!;
  const baseChatRef = useRef<ChatRef | null>(null);
  const [syncInput, setSyncInput] = useState("");
  const [compareChats, setCompareChats] = useState<
    ({ key: string } & ModelOption)[]
  >([{ key: uuidv4(), ...llm2Model }]);
  const chatRefs = useRef<Map<string, ChatRef>>(new Map());

  const syncChatRefs = (ref: ChatRef | null, key: string) => {
    if (ref) {
      chatRefs.current.set(key, ref);
    }
  };
  const onRemoveChat = (key: string) => {
    chatRefs.current.delete(key);
    setCompareChats((ms) => ms.filter((m) => m.key !== key));
  };

  const onAddChat = (index: number, newName: string) => {
    const key = uuidv4();
    setCompareChats((ms) => {
      const newModel = models.find((m) => m.name === newName)!;
      return [...ms.slice(0, index), { ...newModel, key }, ...ms.slice(index)];
    });
  };

  const onSend = (ref: ChatRef) => {
    const refs = [
      ...Array.from(chatRefs.current.values()),
      baseChatRef.current,
    ];
    refs.filter((r) => r !== ref).forEach((c) => c?.send());
    setSyncInput("");
  };

  return baseModel ? (
    <div
      css={css`
        position: absolute;
        inset: 0;
        display: flex;
        overflow: auto;
        flex-wrap: wrap;
        .chat:not(:last-child) {
          border-right: 1px solid ${theme.colorBorder};
        }
      `}
    >
      <div
        className="chat"
        css={css`
          height: 100%;
          flex: 1 0 0;
          display: flex;
        `}
      >
        <Chat
          ref={baseChatRef}
          onSend={() => onSend(baseChatRef.current!)}
          model={baseModel}
          models={models}
          disableAdd={compareChats.length >= 2}
          disableRemove={true}
          syncInput={syncInput}
          onAddChat={(name) => onAddChat(0, name)}
          onSyncInputChanged={setSyncInput}
        />
      </div>
      {compareChats.map((m, index) => (
        <div
          key={m.key}
          className="chat"
          css={css`
            height: 100%;
            flex: 1 0 0;
            display: flex;
          `}
        >
          <Chat
            ref={(ref) => syncChatRefs(ref, m.key)}
            onSend={() => onSend(chatRefs.current.get(m.key)!)}
            model={m}
            models={models}
            disableAdd={compareChats.length >= 2}
            syncInput={syncInput}
            onAddChat={(name) => onAddChat(index, name)}
            onRemoveChat={() => onRemoveChat(m.key)}
            onSyncInputChanged={setSyncInput}
          />
        </div>
      ))}
    </div>
  ) : (
    <div
      css={css`
        position: absolute;
        inset: 0;
        display: flex;
        justify-content: center;
        align-content: center;
        flex-direction: column;
      `}
    >
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No tuna found" />
    </div>
  );
};
