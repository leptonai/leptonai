import { Col, InputNumber, Row, Slider, Typography } from "antd";
import { FC, ReactNode } from "react";

export const SliderOption: FC<{
  title: ReactNode;
  step: number;
  max: number;
  min: number;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}> = ({ title, value, onChange, min, step, max, disabled = false }) => {
  return (
    <>
      <Row justify="space-between">
        <Col flex={0}>
          <Typography.Text strong>{title}</Typography.Text>
        </Col>
        <Col flex={0}>
          <InputNumber
            size="small"
            max={max}
            min={min}
            step={step}
            value={value}
            disabled={disabled}
            onChange={(v) => onChange(v!)}
          />
        </Col>
      </Row>
      <Slider
        disabled={disabled}
        value={value}
        step={step}
        onChange={(v) => onChange(v)}
        max={max}
        min={min}
      />
    </>
  );
};
