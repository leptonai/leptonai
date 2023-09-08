/* eslint-disable @typescript-eslint/no-explicit-any */
import { Col, Row, Space, theme } from "antd";
import {
  ArrayFieldTemplateItemType,
  FormContextType,
  RJSFSchema,
  StrictRJSFSchema,
} from "@rjsf/utils";

const { useToken } = theme;

/** The `ArrayFieldItemTemplate` component is the template used to render an items of an array.
 *
 * @param props - The `ArrayFieldTemplateItemType` props for the component
 */
export default function ArrayFieldItemTemplate<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: ArrayFieldTemplateItemType<T, S, F>) {
  const { token } = useToken();
  const {
    children,
    disabled,
    hasCopy,
    hasMoveDown,
    hasMoveUp,
    hasRemove,
    hasToolbar,
    index,
    onCopyIndexClick,
    onDropIndexClick,
    onReorderClick,
    readonly,
    registry,
    uiSchema,
  } = props;
  const { CopyButton, MoveDownButton, MoveUpButton, RemoveButton } =
    registry.templates.ButtonTemplates;
  const { rowGutter = 24, toolbarAlign = "top" } = registry.formContext;

  return (
    <Row align={toolbarAlign} key={`array-item-${index}`} gutter={rowGutter}>
      <Col flex="1">{children}</Col>
      {hasToolbar && (
        <Col
          flex="128px"
          style={{
            alignSelf: "flex-end",
            paddingBottom: token.marginXXS,
          }}
        >
          <Space style={{ display: "flex", justifyContent: "space-around" }}>
            {(hasMoveUp || hasMoveDown) && (
              <MoveUpButton
                disabled={disabled || readonly || !hasMoveUp}
                onClick={onReorderClick(index, index - 1)}
                uiSchema={uiSchema}
                registry={registry}
              />
            )}
            {(hasMoveUp || hasMoveDown) && (
              <MoveDownButton
                disabled={disabled || readonly || !hasMoveDown}
                onClick={onReorderClick(index, index + 1)}
                uiSchema={uiSchema}
                registry={registry}
              />
            )}
            {hasCopy && (
              <CopyButton
                disabled={disabled || readonly}
                onClick={onCopyIndexClick(index)}
                uiSchema={uiSchema}
                registry={registry}
              />
            )}
            {hasRemove && (
              <RemoveButton
                disabled={disabled || readonly}
                onClick={onDropIndexClick(index)}
                uiSchema={uiSchema}
                registry={registry}
              />
            )}
          </Space>
        </Col>
      )}
    </Row>
  );
}
