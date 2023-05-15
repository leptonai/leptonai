import { FC, PropsWithChildren, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { Divider, Space } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props.ts";

const ItemContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0 8px;
`;

const IconContainer = styled.div`
  flex: 0 0 auto;
`;
const ColonContainer = styled.div`
  flex: 0 0 auto;
  text-align: center;
`;
const TermContainer = styled.div`
  white-space: nowrap;
  flex: 0 0 auto;
`;
const DescriptionContainer = styled.div`
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex: 0 1 auto;
`;

export const Item: FC<
  {
    icon?: ReactNode;
    term?: ReactNode;
    description?: ReactNode;
  } & EmotionProps
> = ({ icon, term, description, className }) => {
  return (
    <ItemContainer className={className}>
      {icon && <IconContainer>{icon}</IconContainer>}
      {term && <TermContainer>{term}</TermContainer>}
      {term && description && <ColonContainer>:</ColonContainer>}
      {description && (
        <DescriptionContainer>{description}</DescriptionContainer>
      )}
    </ItemContainer>
  );
};

export const Container: FC<PropsWithChildren<EmotionProps>> = ({
  children,
  className,
}) => {
  return (
    <Space
      css={css`
        width: 100%;
        .ant-space-item {
          flex: 0 1 auto;
          overflow: hidden;
        }
        .ant-space-item-split {
          flex: 0 0 auto;
        }
      `}
      className={className}
      size={0}
      split={<Divider type="vertical" />}
    >
      {children}
    </Space>
  );
};

export const Description = {
  Item,
  Container,
};
