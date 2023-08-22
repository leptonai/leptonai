import { Copy, Share } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { css as className } from "@emotion/css";
import { Card } from "@lepton-dashboard/components/card";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { FullLayoutWidth } from "@lepton-dashboard/components/layout";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  App,
  Button,
  Col,
  Grid,
  Input,
  Popover,
  Row,
  Skeleton,
  Space,
  Typography,
} from "antd";
import { FC, ReactNode, useCallback } from "react";

export const Container: FC<{
  icon: ReactNode;
  title: ReactNode;
  content: ReactNode;
  option: ReactNode;
  extra?: ReactNode;
  loading: boolean;
}> = ({ icon, title, extra, content, option, loading }) => {
  const theme = useAntdTheme();
  const { md } = Grid.useBreakpoint();
  const { message } = App.useApp();

  const copy = useCallback(() => {
    void navigator.clipboard.writeText(location.href);
    void message.success("Copied");
  }, [message]);
  return (
    <FullLayoutWidth>
      <Card
        css={css`
          flex: 1;
        `}
        bodyClassName={className`
          display: flex;
          flex-direction: column;
        `}
        paddingless
        icon={icon}
        title={title}
        extra={
          <Space size={0}>
            {extra}
            <Popover
              placement="bottomRight"
              trigger={["click"]}
              content={
                <div>
                  <Typography.Paragraph type="secondary">
                    Anyone who has this link will be able to view this
                  </Typography.Paragraph>
                  <Space.Compact
                    css={css`
                      width: 350px;
                    `}
                  >
                    <Input value={location.href} readOnly />
                    <Button
                      onClick={copy}
                      type="primary"
                      icon={<CarbonIcon icon={<Copy />} />}
                    />
                  </Space.Compact>
                </div>
              }
            >
              <Button
                type="text"
                size="small"
                icon={<CarbonIcon icon={<Share />} />}
              >
                Share
              </Button>
            </Popover>
          </Space>
        }
      >
        {loading ? (
          <Card borderless>
            <Skeleton active />
          </Card>
        ) : (
          <Row
            gutter={[0, 0]}
            css={css`
              flex: 1;
            `}
          >
            <Col span={24} sm={24} md={17} xl={19} xxl={20}>
              <div
                css={css`
                  padding: 16px;
                  height: 100%;
                  display: flex;
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
