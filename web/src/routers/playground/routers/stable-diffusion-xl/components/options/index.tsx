import { SliderOption } from "@lepton-libs/gradio/slider-option";
import { Checkbox, Col, Row, Typography } from "antd";
import { FC } from "react";

export interface SdxlOption {
  width: number; // float (numeric value between 768 and 1024)
  height: number; // float (numeric value between 768 and 1024)
  seed: number; // float (numeric value between 0 and 2147483647)
  num_inference_steps: number; // float (numeric value between 1 and 50)
  use_refiner: boolean;
}
export const Options: FC<{
  value: SdxlOption;
  onChange: (v: SdxlOption) => void;
}> = ({ value, onChange }) => {
  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <SliderOption
          title="Width"
          min={768}
          max={1024}
          step={1}
          onChange={(width) => onChange({ ...value, width })}
          value={value.width}
        />
      </Col>
      <Col span={24}>
        <SliderOption
          title="Height"
          min={768}
          max={1024}
          step={1}
          onChange={(height) => onChange({ ...value, height })}
          value={value.height}
        />
      </Col>
      <Col span={24}>
        <SliderOption
          title="Seed"
          min={0}
          max={2147483647}
          step={1}
          onChange={(seed) => onChange({ ...value, seed })}
          value={value.seed}
        />
      </Col>
      <Col span={24}>
        <SliderOption
          title="Steps"
          min={1}
          max={50}
          step={1}
          onChange={(num_inference_steps) =>
            onChange({ ...value, num_inference_steps })
          }
          value={value.num_inference_steps}
        />
      </Col>
      <Col span={24}>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Text strong>Use Refiner</Typography.Text>
          </Col>
          <Col flex={0}>
            <Checkbox
              onChange={(v) =>
                onChange({ ...value, use_refiner: v.target.checked })
              }
              checked={value.use_refiner}
            />
          </Col>
        </Row>
      </Col>
    </Row>
  );
};