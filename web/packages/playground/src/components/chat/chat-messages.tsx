import { Scrollable, ScrollableRef } from "@lepton/ui/components/scrollable";
import { MessageLoading } from "./message-loading";
import { ChatMessageItem, isUserMessage } from "../../shared/chat";
import { MDMessage } from "./md-message";
import { Avatar, AvatarFallback } from "@lepton/ui/components/avatar";
import { forwardRef } from "react";
import { ChatBot, Carbon, UserAvatarFilledAlt } from "@carbon/icons-react";
import { cn } from "@lepton/ui/utils";

export const ChatMessages = forwardRef<
  ScrollableRef,
  { messages: ChatMessageItem[] }
>(({ messages }, ref) => {
  return (
    <Scrollable
      ref={ref}
      margin="8px"
      position={["start", "end"]}
      className="bg-background flex-1 w-full"
    >
      {messages.length > 0 ? (
        <>
          {messages.map((item, index) => {
            const loading =
              item.loading &&
              (!item.responseTime ||
                (!item.completionTime && !item.message.content));
            return (
              <div
                key={index}
                className={cn(
                  "border p-4",
                  index === messages.length - 1
                    ? "border-transparent"
                    : "border-border",
                  isUserMessage(item)
                    ? "bg-muted"
                    : item.error
                    ? "bg-destructive/[0.1]"
                    : "bg-background"
                )}
              >
                <div className="max-w[800px] m[x-auto]">
                  <div className="flex flex-row items-start">
                    <div className="leading-none mr-[16px]">
                      {isUserMessage(item) ? (
                        <Avatar className="w-6 h-6">
                          <AvatarFallback className="bg-primary text-primary-foreground">
                            <UserAvatarFilledAlt size={16} />
                          </AvatarFallback>
                        </Avatar>
                      ) : (
                        <Avatar className="w-6 h-6">
                          <AvatarFallback className="text-white bg-sky-600">
                            <Carbon size={16} />
                          </AvatarFallback>
                        </Avatar>
                      )}
                    </div>

                    <div className="overflow-hidden leading-[24px]">
                      {loading ? (
                        <MessageLoading />
                      ) : (
                        <MDMessage
                          content={item.message.content}
                          error={item.error}
                          loading={item.loading}
                          responseTime={item.responseTime}
                          completionTime={
                            item.message.role === "user"
                              ? 1
                              : item.completionTime
                          }
                        />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </>
      ) : (
        <div className="flex flex-col justify-center items-center h-full">
          <ChatBot className="w-40 h-40 opacity-30 text-muted-foreground/[.3]" />
        </div>
      )}
    </Scrollable>
  );
});

ChatMessages.displayName = "ChatMessages";
