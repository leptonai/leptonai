import {
  AddAlt,
  Code,
  NonCertified,
  Settings,
  SubtractAlt,
} from "@carbon/icons-react";
import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { CarbonIcon, TunaIcon } from "@lepton-dashboard/components/icons";

import { ApiModal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/api-modal";
import {
  ChatBox,
  ChatRef,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats/components/chat-box";
import { OpenaiSettings } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats/components/openai-settings";
import {
  ChatOption,
  ChatService,
  ModelOption,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import pathJoin from "@lepton-libs/url/path-join";
import { Button, Dropdown, Popover, Space, Tooltip } from "antd";
import { forwardRef, useMemo, useState } from "react";

export const Chat = forwardRef<
  ChatRef,
  {
    model: ModelOption;
    models: ModelOption[];
    syncInput: string;
    onSyncInputChanged: (v: string) => void;
    onSend: () => void;
    onAddChat?: (name: string) => void;
    onRemoveChat?: (name: string) => void;
    disableAdd?: boolean;
    disableRemove?: boolean;
  }
>(
  (
    {
      model,
      onSyncInputChanged,
      syncInput,
      onSend,
      models,
      onAddChat,
      onRemoveChat,
      disableRemove = false,
      disableAdd = false,
    },
    ref
  ) => {
    const [loading, setLoading] = useState(false);
    const chatService = useInject(ChatService);
    const workspaceTrackerService = useInject(WorkspaceTrackerService);
    const chat = useMemo(
      () =>
        chatService.createChat({
          api_url: pathJoin(model.apiOption.api_url, "chat/completions"),
          api_key: model.apiOption.api_key,
        }),
      [chatService, model]
    );
    const [option, setOption] = useState<ChatOption>({
      max_tokens: 512,
      top_p: 0.8,
      temperature: 0.5,
    });

    return (
      <Card
        css={css`
          height: 100%;
          flex: 1 0 0;
        `}
        icon={<TunaIcon />}
        extra={
          <Space size={0}>
            <Tooltip title="Clear conversation">
              <Button
                disabled={loading}
                onClick={() => chat?.clear()}
                type="text"
                icon={<CarbonIcon icon={<NonCertified />} />}
              />
            </Tooltip>
            <Tooltip title="Add tuna chat for comparison">
              <Dropdown
                arrow={true}
                disabled={disableAdd}
                trigger={["click"]}
                menu={{
                  items: models.map((m) => ({
                    key: m.name,
                    label: m.name,
                    onClick: () => onAddChat && onAddChat(m.name),
                  })),
                }}
              >
                <Button
                  disabled={disableAdd}
                  type="text"
                  icon={<CarbonIcon icon={<AddAlt />} />}
                />
              </Dropdown>
            </Tooltip>
            <Tooltip title="Hide tuna chat">
              <Button
                disabled={disableRemove}
                onClick={() => onRemoveChat && onRemoveChat(model.name)}
                type="text"
                icon={<CarbonIcon icon={<SubtractAlt />} />}
              />
            </Tooltip>
            <ApiModal
              icon={<CarbonIcon icon={<Code />} />}
              name={model.name}
              apiUrl={model.apiOption.api_url}
              apiKey={model.apiOption.api_key}
            />
            <Tooltip title="Configure tuna chat">
              <Popover
                trigger={["click"]}
                content={
                  <div
                    css={css`
                      width: 200px;
                    `}
                  >
                    <OpenaiSettings
                      chatOption={option}
                      onChatOptionChanged={setOption}
                    />
                  </div>
                }
                placement="bottomRight"
              >
                <Button type="text" icon={<CarbonIcon icon={<Settings />} />} />
              </Popover>
            </Tooltip>
          </Space>
        }
        title={model.name}
        paddingless
        borderless
      >
        <div
          css={css`
            position: absolute;
            inset: 0;
            overflow: auto;
          `}
        >
          {chat ? (
            <ChatBox
              chatOption={option}
              onSend={onSend}
              onLoadingChanged={setLoading}
              chat={chat}
              ref={ref}
              disabled={workspaceTrackerService.workspace?.isPastDue}
              syncInput={syncInput}
              onInputChanged={onSyncInputChanged}
            />
          ) : (
            <Card loading borderless />
          )}
        </div>
      </Card>
    );
  }
);
