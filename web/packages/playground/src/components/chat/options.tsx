import { ChatOption } from "../../shared/chat";
import { SliderOption } from "../slider-option";
import { FC } from "react";

export const Options: FC<{
  chatOption: ChatOption;
  onChatOptionChanged: (option: ChatOption) => void;
}> = ({ chatOption, onChatOptionChanged }) => {
  return (
    <div className="flex flex-col space-y-4">
      <SliderOption
        title="Temperature"
        min={0}
        max={1}
        step={0.01}
        onChange={(temperature) =>
          onChatOptionChanged({ ...chatOption, temperature })
        }
        value={chatOption.temperature}
      />
      <SliderOption
        title="Max tokens"
        min={16}
        max={972}
        step={64}
        integer
        onChange={(max_tokens) =>
          onChatOptionChanged({ ...chatOption, max_tokens })
        }
        value={chatOption.max_tokens}
      />
      <SliderOption
        title="Top P"
        min={0}
        max={1}
        step={0.01}
        onChange={(top_p) => onChatOptionChanged({ ...chatOption, top_p })}
        value={chatOption.top_p}
      />
    </div>
  );
};
