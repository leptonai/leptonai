import { ChatOption } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";
import { Col, Row, Slider, Typography } from "antd";
import { FC } from "react";

export const OpenaiSettings: FC<{
  chatOption: ChatOption;
  onChatOptionChanged: (option: ChatOption) => void;
}> = ({ chatOption, onChatOptionChanged }) => {
  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Text strong>Temperature</Typography.Text>
          </Col>
          <Col flex={0}>
            <Typography.Text>{chatOption.temperature}</Typography.Text>
          </Col>
        </Row>
        <Slider
          value={chatOption.temperature}
          step={0.01}
          onChange={(temperature) =>
            onChatOptionChanged({ ...chatOption, temperature })
          }
          max={1}
          min={0}
        />
      </Col>
      <Col span={24}>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Text strong>Maximum length</Typography.Text>
          </Col>
          <Col flex={0}>
            <Typography.Text>{chatOption.max_tokens}</Typography.Text>
          </Col>
        </Row>
        <Slider
          value={chatOption.max_tokens}
          step={64}
          onChange={(max_tokens) =>
            onChatOptionChanged({ ...chatOption, max_tokens })
          }
          max={972}
          min={16}
        />
      </Col>
      <Col span={24}>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Text strong>Top P</Typography.Text>
          </Col>
          <Col flex={0}>
            <Typography.Text>{chatOption.top_p}</Typography.Text>
          </Col>
        </Row>
        <Slider
          value={chatOption.top_p}
          step={0.01}
          onChange={(top_p) => onChatOptionChanged({ ...chatOption, top_p })}
          max={1}
          min={0}
        />
      </Col>
    </Row>
  );
};
