import { ChatBot, User } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon, TunaIcon } from "@lepton-dashboard/components/icons";
import {
  Scrollable,
  ScrollableRef,
} from "@lepton-dashboard/components/scrollable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { MessageLoading } from "@lepton-libs/gradio/message-loading";
import { ChatMessageItem, ChatService } from "@lepton-libs/gradio/chat.service";
import { Avatar, Space, Typography } from "antd";
import { forwardRef } from "react";

export const ChatMessages = forwardRef<
  ScrollableRef,
  { messages: ChatMessageItem[] }
>(({ messages }, ref) => {
  const theme = useAntdTheme();
  return (
    <Scrollable
      ref={ref}
      margin="8px"
      position={["start", "end"]}
      css={css`
        flex: 1;
        width: 100%;
        background-color: ${theme.colorBgContainer};
      `}
    >
      {messages.length > 0 ? (
        <>
          {messages.map((item, index) => {
            const loading = item.loading && !item.responseTime;
            return (
              <div
                key={index}
                css={css`
                  border-bottom: 1px solid
                    ${index === messages.length - 1
                      ? "transparent"
                      : theme.colorBorderSecondary};
                  background: ${ChatService.isUserMessage(item)
                    ? theme.colorBgLayout
                    : item.error
                    ? theme.colorErrorBg
                    : theme.colorBgContainer};
                  padding: ${theme.paddingSM}px;
                `}
              >
                <div
                  css={css`
                    max-width: 800px;
                    margin: 0 auto;
                  `}
                >
                  <div>
                    {!ChatService.isUserMessage(item) && (
                      <Typography.Text
                        type="secondary"
                        css={css`
                          display: block;
                          font-size: ${theme.fontSizeSM}px;
                          margin-left: 40px;
                        `}
                      >
                        {loading ? (
                          <>Generating...</>
                        ) : (
                          <>
                            response in{" "}
                            {item.responseTime
                              ? (item.responseTime / 1000).toFixed(2)
                              : "N/A "}
                            s, completion in{" "}
                            {item.completionTime
                              ? (item.completionTime / 1000).toFixed(2)
                              : "N/A "}
                            s
                          </>
                        )}
                      </Typography.Text>
                    )}
                    <Space align="start" size={16}>
                      <div
                        css={css`
                          line-height: 0;
                        `}
                      >
                        {ChatService.isUserMessage(item) ? (
                          <Avatar
                            size="small"
                            css={css`
                              background: ${theme.colorTextHeading};
                              color: ${theme.colorBgContainer};
                            `}
                            icon={<CarbonIcon icon={<User />} />}
                          />
                        ) : (
                          <Avatar
                            size="small"
                            css={css`
                              background: ${theme.colorTheme};
                              color: ${theme.colorBgContainer};
                            `}
                            icon={<TunaIcon />}
                          />
                        )}
                      </div>

                      {loading ? (
                        <div
                          css={css`
                            line-height: 0;
                          `}
                        >
                          <MessageLoading />
                        </div>
                      ) : (
                        <Typography.Text
                          type={item.error ? "danger" : undefined}
                          css={css`
                            position: relative;
                            top: 1px;
                          `}
                        >
                          <pre
                            css={css`
                              font-family: ${theme.fontFamily} !important;
                              padding: 0 !important;
                              margin: 0 !important;
                              white-space: pre-wrap;
                              word-wrap: break-word;
                              background: transparent !important;
                              border: none !important;
                              border-radius: 0 !important;
                            `}
                          >
                            {item.error || item.message.content.trim()}
                          </pre>
                        </Typography.Text>
                      )}
                    </Space>
                  </div>
                </div>
              </div>
            );
          })}
        </>
      ) : (
        <div
          css={css`
            display: flex;
            flex: 1;
            height: 100%;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-size: 128px;
            opacity: 0.3;
            color: ${theme.colorBorderSecondary};
          `}
        >
          <CarbonIcon icon={<ChatBot />} />
        </div>
      )}
    </Scrollable>
  );
});
