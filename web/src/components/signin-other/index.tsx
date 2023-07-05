import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Button, Col, Row, Typography } from "antd";
import { FC } from "react";
import { useNavigate } from "react-router-dom";

export const SignAsOther: FC<{
  heading?: string;
  tips?: string;
  waitlist?: boolean;
}> = ({ heading, tips, waitlist = false }) => {
  const navigate = useNavigate();
  const profileService = useInject(ProfileService);
  return (
    <CenterBox>
      {heading && (
        <Typography.Title
          level={3}
          css={css`
            margin-top: 0;
          `}
        >
          {heading}
        </Typography.Title>
      )}
      {tips && <Typography.Paragraph>{tips}</Typography.Paragraph>}
      {profileService.profile?.oauth?.id ? (
        <>
          <Typography.Paragraph>
            You are logged in as{" "}
            <strong>{profileService.profile?.oauth?.email}</strong>
          </Typography.Paragraph>
          <Row gutter={[16, 16]}>
            {waitlist && (
              <Col flex={1}>
                <Button
                  block
                  size="large"
                  type="primary"
                  onClick={() => navigate("/waitlist", { relative: "route" })}
                >
                  Join waitlist
                </Button>
              </Col>
            )}
            <Col flex={1}>
              <Button
                block
                type="primary"
                size="large"
                onClick={() => navigate("/login", { relative: "route" })}
              >
                Switch user
              </Button>
            </Col>
          </Row>
        </>
      ) : (
        <>
          <Typography.Paragraph>
            Or the token is invalid or expired
          </Typography.Paragraph>
          <Button
            size="large"
            type="primary"
            onClick={() => navigate("/login", { relative: "route" })}
          >
            Try a different token
          </Button>
        </>
      )}
    </CenterBox>
  );
};
