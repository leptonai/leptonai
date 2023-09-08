import { FC, PropsWithChildren, ReactNode } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { Divider, Space } from "antd";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

const ItemContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0 8px;
`;

const IconContainer = styled.div`
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
`;
const ColonContainer = styled.div`
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
`;
const TermContainer = styled.div`
  white-space: nowrap;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
`;
const DescriptionContainer = styled.div`
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex: 0 0 auto;
  width: 100%;
`;

export const Item: FC<
  {
    icon?: ReactNode;
    term?: ReactNode;
    description?: ReactNode;
    hideMark?: boolean;
  } & EmotionProps
> = ({ icon, term, hideMark, description, className }) => {
  const theme = useAntdTheme();
  return (
    <ItemContainer className={className}>
      {icon && (
        <IconContainer
          css={css`
            color: ${theme.colorTextSecondary};
          `}
        >
          {icon}
        </IconContainer>
      )}
      {term && <TermContainer>{term}</TermContainer>}
      {term !== undefined && description != undefined && !hideMark && (
        <ColonContainer>:</ColonContainer>
      )}
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
      align="center"
      css={css`
        width: 100%;
        .ant-space-item {
          flex: 0 0 auto;
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
