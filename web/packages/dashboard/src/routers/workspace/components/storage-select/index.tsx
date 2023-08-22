import { LoadingOutlined } from "@ant-design/icons";
import { Folder } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  StorageTree,
  StorageTreeProps,
} from "@lepton-dashboard/routers/workspace/components/storage-tree";
import { FC, useRef, useState } from "react";
import { Dropdown, Input, InputRef } from "antd";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export type StorageSelectProps = StorageTreeProps & {
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  readonly?: boolean;
  placeholder?: string;
};
export const StorageSelect: FC<StorageSelectProps> = ({
  nodeFilter,
  onInitialized,
  onInitializedFailed,
  nodeDisabler,
  disabled,
  placeholder,
  value,
  onChange,
}) => {
  const theme = useAntdTheme();
  const [initialized, setInitialized] = useState(false);
  const [innerValue, setInnerValue] = useState<string | undefined>(value);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<InputRef>(null);

  return (
    <Dropdown
      disabled={disabled}
      open={open}
      trigger={["click"]}
      onOpenChange={setOpen}
      dropdownRender={() => {
        return (
          <div
            style={{
              visibility: initialized ? "visible" : "hidden",
            }}
            css={css`
              min-height: 40px;
              max-height: 50vh;
              max-width: 100vw;
              background: ${theme.colorBgContainer};
              padding: ${theme.paddingSM}px;
              border-radius: ${theme.borderRadiusLG};
              box-shadow: ${theme.boxShadowSecondary};
              overflow: auto;
            `}
          >
            <StorageTree
              disabled={disabled}
              nodeFilter={nodeFilter}
              nodeDisabler={nodeDisabler}
              onInitialized={() => {
                setInitialized(true);
                onInitialized?.();
              }}
              onInitializedFailed={onInitializedFailed}
              onSelectedKeysChanged={(keys) => {
                setInnerValue(keys[0]);
                onChange?.(keys[0]);
                setOpen(false);
                inputRef.current?.focus();
              }}
            />
          </div>
        );
      }}
    >
      <Input
        disabled={disabled}
        ref={inputRef}
        placeholder={placeholder}
        value={innerValue}
        onChange={(e) => {
          setInnerValue(e.target.value);
          onChange?.(e.target.value);
        }}
        addonBefore={
          open && !initialized ? (
            <LoadingOutlined />
          ) : (
            <CarbonIcon icon={<Folder />} />
          )
        }
      />
    </Dropdown>
  );
};
