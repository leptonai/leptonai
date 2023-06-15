import { Alert, List, Space, theme } from "antd";
import ExclamationCircleOutlined from "@ant-design/icons/ExclamationCircleOutlined";
import {
  ErrorListProps,
  FormContextType,
  RJSFSchema,
  StrictRJSFSchema,
  TranslatableString,
} from "@rjsf/utils";
import { useMemo } from "react";
import styled from "@emotion/styled";

/** The `ErrorList` component is the template that renders the all the errors associated with the fields in the `Form`
 *
 * @param props - The `ErrorListProps` for this component
 */
export default function ErrorList<
  T = any,
  S extends StrictRJSFSchema = RJSFSchema,
  F extends FormContextType = any
>({ errors, registry }: ErrorListProps<T, S, F>) {
  const { translateString } = registry;

  const { token } = theme.useToken();

  const StyledAlert = useMemo(
    () => styled(Alert)`
      margin-bottom: ${token.marginXL}px;
      padding-bottom: 0;

      .list-group .ant-list-item {
        padding-left: 0;
        padding-right: 0;

        .anticon.anticon-exclamation-circle {
          color: ${token.colorError};
        }
      }
    `,
    [token]
  );

  const renderErrors = () => (
    <List className="list-group" size="small">
      {errors.map((error, index) => (
        <List.Item key={index}>
          <Space>
            <ExclamationCircleOutlined />
            {error.stack}
          </Space>
        </List.Item>
      ))}
    </List>
  );

  return (
    <StyledAlert
      className="panel panel-danger errors"
      description={renderErrors()}
      message={translateString(TranslatableString.ErrorsLabel)}
      type="error"
    />
  );
}
