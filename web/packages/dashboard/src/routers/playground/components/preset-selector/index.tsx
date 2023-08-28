import { Select } from "antd";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC } from "react";
import { css } from "@emotion/react";

export const PresetSelector: FC<{
  value?: string;
  onChange: (v: string) => void;
  options?: { label: string; value: string; placeholder: string }[];
}> = ({ value, onChange, options }) => {
  const theme = useAntdTheme();
  return (
    <Select
      css={css`
        width: 130px;
        .ant-select-selection-placeholder,
        .ant-select-arrow {
          font-weight: normal;
          color: ${theme.colorText};
        }
      `}
      popupMatchSelectWidth={false}
      options={options}
      optionLabelProp="placeholder"
      value={value}
      onChange={onChange}
      size="small"
      bordered={false}
      placeholder="Load a preset"
    />
  );
};
