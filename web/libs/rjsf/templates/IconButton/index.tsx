import { Button } from "antd";
import type { ButtonProps } from "antd";
import type { BaseButtonProps } from "antd/es/button/button";
import ArrowDownOutlined from "@ant-design/icons/ArrowDownOutlined";
import ArrowUpOutlined from "@ant-design/icons/ArrowUpOutlined";
import CopyOutlined from "@ant-design/icons/CopyOutlined";
import PlusOutlined from "@ant-design/icons/PlusOutlined";
import MinusOutlined from "@ant-design/icons/MinusOutlined";
import {
  FormContextType,
  getUiOptions,
  IconButtonProps,
  RJSFSchema,
  StrictRJSFSchema,
  TranslatableString,
} from "@rjsf/utils";

// The `type` for IconButtonProps collides with the `type` for `ButtonProps` so omit it to avoid Typescript issue
export type AntdIconButtonProps<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
> = Omit<IconButtonProps<T, S, F>, "type">;

export default function IconButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F> & BaseButtonProps) {
  const {
    iconType = "default",
    icon,
    uiSchema,
    registry,
    onClick,
    ...otherProps
  } = props;
  return (
    <Button
      type={iconType as ButtonProps["type"]}
      onClick={onClick as ButtonProps["onClick"]}
      icon={icon}
      {...otherProps}
    />
  );
}

export function AddButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F>) {
  const {
    registry: { translateString },
  } = props;
  return (
    <IconButton
      title={translateString(TranslatableString.AddItemButton)}
      {...props}
      block
      iconType="dashed"
      icon={<PlusOutlined />}
    />
  );
}

export function CopyButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F>) {
  const {
    registry: { translateString },
  } = props;
  return (
    <IconButton
      title={translateString(TranslatableString.CopyButton)}
      {...props}
      iconType="text"
      icon={<CopyOutlined />}
    />
  );
}

export function MoveDownButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F>) {
  const {
    registry: { translateString },
  } = props;
  return (
    <IconButton
      title={translateString(TranslatableString.MoveDownButton)}
      {...props}
      iconType="text"
      icon={<ArrowDownOutlined />}
    />
  );
}

export function MoveUpButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F>) {
  const {
    registry: { translateString },
  } = props;
  return (
    <IconButton
      title={translateString(TranslatableString.MoveUpButton)}
      {...props}
      iconType="text"
      icon={<ArrowUpOutlined />}
    />
  );
}

export function RemoveButton<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: AntdIconButtonProps<T, S, F>) {
  // The `block` prop is not part of the `IconButtonProps` defined in the template, so get it from the uiSchema instead
  const options = getUiOptions<T, S, F>(props.uiSchema);
  const {
    registry: { translateString },
  } = props;
  return (
    <IconButton
      title={translateString(TranslatableString.RemoveButton)}
      {...props}
      block={!!options.block}
      iconType="text"
      icon={<MinusOutlined />}
    />
  );
}
