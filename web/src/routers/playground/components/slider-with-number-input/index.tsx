import { FC, useCallback, useState } from "react";
import { InputNumber, Slider } from "antd";
import { css } from "@emotion/react";

export const SliderWithNumberInput: FC<{
  value?: number;
  onChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  integer?: boolean;
}> = ({
  value = 0,
  onChange = () => void 0,
  min = 0,
  max = Number.MAX_SAFE_INTEGER,
  step = 1,
  integer = false,
}) => {
  const [innerValue, setInnerValue] = useState(value);

  const innerOnChange = (value: number | string | null) => {
    if (typeof value === "number") {
      setInnerValue(value);
      onChange(value);
    }
  };

  const parser = useCallback(
    (value: string | undefined) => {
      if (value === undefined) {
        return 0;
      }
      if (integer) {
        return parseInt(value, 10);
      }
      return parseFloat(value);
    },
    [integer]
  );

  return (
    <div
      css={css`
        display: inline-flex;
        flex-wrap: nowrap;
        width: 100%;
      `}
    >
      <Slider
        css={css`
          flex: 1;
          margin-right: 16px;
        `}
        min={min}
        max={max}
        step={step}
        value={innerValue}
        onChange={innerOnChange}
      />
      <InputNumber
        css={css`
          flex: 0 0 100px;
        `}
        parser={parser}
        min={min}
        max={max}
        step={step}
        onChange={innerOnChange}
        value={innerValue}
      />
    </div>
  );
};
