import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { Col, Progress, Row, Typography } from "antd";
import { FC } from "react";

export const Quota: FC<{
  used: number;
  limit: number;
  name: string;
  unit: string;
}> = ({ used, limit, name, unit }) => {
  const progress = (used / limit) * 100;
  return (
    <Card
      shadowless
      borderless
      paddingless
      css={css`
        background: transparent;
      `}
    >
      <Row
        justify="space-between"
        css={css`
          display: flex;
          align-items: center;
        `}
      >
        <Col flex={0}>
          <Typography.Title
            css={css`
              margin: 0 12px 0 0 !important;
            `}
            level={5}
          >
            {name}
          </Typography.Title>
        </Col>
        <Col flex={0}>
          <Typography.Text type="secondary">
            {`${used} of ${limit} ${unit} used`}
          </Typography.Text>
        </Col>
      </Row>

      <Progress
        css={css`
          margin: 0;
          .ant-progress-inner,
          .ant-progress-bg {
            border-radius: 0 !important;
          }
        `}
        showInfo={false}
        size={["100%", 2]}
        percent={progress}
        status={progress > 80 ? "exception" : "success"}
      />
    </Card>
  );
};
