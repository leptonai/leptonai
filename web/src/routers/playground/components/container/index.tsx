import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { FullLayoutWidth } from "@lepton-dashboard/components/layout";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Col, Grid, Row, Skeleton } from "antd";
import { FC, ReactNode } from "react";

export const Container: FC<{
  icon: ReactNode;
  title: ReactNode;
  content: ReactNode;
  option: ReactNode;
  loading: boolean;
}> = ({ icon, title, content, option, loading }) => {
  const theme = useAntdTheme();
  const { md } = Grid.useBreakpoint();
  return (
    <FullLayoutWidth>
      <Card paddingless icon={icon} title={title}>
        {loading ? (
          <Card borderless>
            <Skeleton active />
          </Card>
        ) : (
          <Row gutter={[0, 0]}>
            <Col span={24} sm={24} md={17} xl={19} xxl={20}>
              <div
                css={css`
                  padding: 16px;
                `}
              >
                {content}
              </div>
            </Col>
            <Col
              span={24}
              xxl={4}
              xl={5}
              sm={24}
              md={7}
              css={css`
                border-left: ${!md ? 0 : "1px"} solid ${theme.colorBorder};
              `}
            >
              <div
                css={css`
                  padding: 16px;
                `}
              >
                {option}
              </div>
            </Col>
          </Row>
        )}
      </Card>
    </FullLayoutWidth>
  );
};
