import {
  ArrayFieldTemplateItemType,
  ArrayFieldTemplateProps,
  FormContextType,
  getTemplate,
  getUiOptions,
  RJSFSchema,
  StrictRJSFSchema,
} from "@rjsf/utils";
import { Space } from "antd";

import styled from "@emotion/styled";

const Fieldset = styled.fieldset`
  all: unset;
  display: block;

  .form-group.field-object {
    margin-bottom: 0;

    .panel.panel-default.panel-body {
      margin-bottom: 0;
    }
  }

  .panel.panel-default.panel-body
    &
    > .ant-space
    > .ant-space-item:first-child:has(label) {
    display: none;
  }
`;

/** The `ArrayFieldTemplate` component is the template used to render all items in an array.
 *
 * @param props - The `ArrayFieldTemplateItemType` props for the component
 */
export default function ArrayFieldTemplate<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>(props: ArrayFieldTemplateProps<T, S, F>) {
  const {
    canAdd,
    className,
    disabled,
    idSchema,
    items,
    onAddClick,
    readonly,
    registry,
    required,
    schema,
    title,
    uiSchema,
  } = props;
  const uiOptions = getUiOptions<T, S, F>(uiSchema);
  const ArrayFieldDescriptionTemplate = getTemplate<
    "ArrayFieldDescriptionTemplate",
    T,
    S,
    F
  >("ArrayFieldDescriptionTemplate", registry, uiOptions);
  const ArrayFieldItemTemplate = getTemplate<"ArrayFieldItemTemplate", T, S, F>(
    "ArrayFieldItemTemplate",
    registry,
    uiOptions
  );
  const ArrayFieldTitleTemplate = getTemplate<
    "ArrayFieldTitleTemplate",
    T,
    S,
    F
  >("ArrayFieldTitleTemplate", registry, uiOptions);
  // Button templates are not overridden in the uiSchema
  const {
    ButtonTemplates: { AddButton },
  } = registry.templates;

  return (
    <Fieldset className={className} id={idSchema.$id}>
      <Space direction="vertical" size="small" style={{ display: "flex" }}>
        {(uiOptions.title || title) && (
          <ArrayFieldTitleTemplate
            idSchema={idSchema}
            required={required}
            title={uiOptions.title || title}
            schema={schema}
            uiSchema={uiSchema}
            registry={registry}
          />
        )}
        {(uiOptions.description || schema.description) && (
          <ArrayFieldDescriptionTemplate
            description={uiOptions.description || schema.description}
            idSchema={idSchema}
            schema={schema}
            uiSchema={uiSchema}
            registry={registry}
          />
        )}
        {items &&
          items.map(
            ({ key, ...itemProps }: ArrayFieldTemplateItemType<T, S, F>) => (
              <ArrayFieldItemTemplate key={key} {...itemProps} />
            )
          )}
        {canAdd && (
          <AddButton
            className="array-item-add"
            disabled={disabled || readonly}
            onClick={onAddClick}
            uiSchema={uiSchema}
            registry={registry}
          />
        )}
      </Space>
    </Fieldset>
  );
}
