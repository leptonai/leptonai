import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, useCallback, useMemo, useRef, useState } from "react";
import { Col, Row } from "antd";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useParams } from "react-router-dom";
import {
  Chat,
  ChatRef,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chat-models-comparison/components/chat";
import { ChatHeader } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chat-models-comparison/components/chat-header";
import { ChatContainer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chat-models-comparison/components/chat-container";
import {
  benchmarkModel,
  ChatService,
  ModelOption,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";
import { useInject } from "@lepton-libs/di";
import pathJoin from "@lepton-libs/url/path-join";
export interface ChatModelsComparisonProps {
  name: string;
}

export const ChatModelsComparison: FC<ChatModelsComparisonProps> = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const { name } = useParams<{ name: string }>();
  const theme = useAntdTheme();
  const chatService = useInject(ChatService);
  const [syncInput, setSyncInput] = useState("");
  const [leftModel, setLeftModel] = useState<ModelOption | null>(
    benchmarkModel
  );
  const [rightModel, setRightModel] = useState<ModelOption | null>(null);
  const sidesRef = useRef({
    left: null as null | ChatRef,
    right: null as null | ChatRef,
  });

  const leftChat = useMemo(
    () =>
      leftModel
        ? chatService.createChat({
            api_url: pathJoin(leftModel.apiOption.api_url, "chat/completions"),
            api_key: leftModel.apiOption.api_key,
          })
        : null,
    [chatService, leftModel]
  );

  const rightChat = useMemo(
    () =>
      rightModel
        ? chatService.createChat({
            api_url: pathJoin(rightModel.apiOption.api_url, "chat/completions"),
            api_key: rightModel.apiOption.api_key,
          })
        : null,
    [chatService, rightModel]
  );

  const onSendFrom = useCallback((key: string) => {
    const map = sidesRef.current || {};
    (Object.keys(map) as (keyof typeof map)[])
      .filter((k) => k !== key)
      .forEach((k) => {
        map[k]?.send();
      });
    setSyncInput("");
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
        <ChatContainer
          header={
            <ChatHeader
              chat={leftChat}
              modelName={benchmarkModel.name}
              onModelChange={setLeftModel}
            />
          }
        >
          <Chat
            chat={leftChat}
            disabled={
              !leftModel || workspaceTrackerService.workspace?.isPastDue
            }
            ref={(ref) => {
              sidesRef.current["left"] = ref;
            }}
            syncInput={syncInput}
            onInputChanged={setSyncInput}
            onSend={() => onSendFrom("left")}
          />
        </ChatContainer>
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
        <ChatContainer
          header={
            <ChatHeader
              chat={rightChat}
              modelName={name || benchmarkModel.name}
              onModelChange={setRightModel}
            />
          }
        >
          <Chat
            chat={rightChat}
            ref={(ref) => {
              sidesRef.current["right"] = ref;
            }}
            disabled={
              !rightModel || workspaceTrackerService.workspace?.isPastDue
            }
            syncInput={syncInput}
            onInputChanged={setSyncInput}
            onSend={() => onSendFrom("right")}
          />
        </ChatContainer>
      </Col>
    </Row>
  );
};
