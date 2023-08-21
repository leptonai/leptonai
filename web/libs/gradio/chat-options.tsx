import { ChatOption } from "@lepton-libs/gradio/chat.service";
import { SliderOption } from "@lepton-libs/gradio/slider-option";
import { Col, Row } from "antd";
import { FC } from "react";

export const ChatOptions: FC<{
  chatOption: ChatOption;
  onChatOptionChanged: (option: ChatOption) => void;
}> = ({ chatOption, onChatOptionChanged }) => {
  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
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
      </Col>
      <Col span={24}>
        <SliderOption
          title="Maximum length"
          min={16}
          max={972}
          step={64}
          onChange={(max_tokens) =>
            onChatOptionChanged({ ...chatOption, max_tokens })
          }
          value={chatOption.max_tokens}
        />
      </Col>
      <Col span={24}>
        <SliderOption
          title="Top P"
          min={0}
          max={1}
          step={0.01}
          onChange={(top_p) => onChatOptionChanged({ ...chatOption, top_p })}
          value={chatOption.top_p}
        />
      </Col>
    </Row>
  );
};
