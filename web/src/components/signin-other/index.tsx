import {
  GithubOutlined,
  ReadOutlined,
  TwitterOutlined,
} from "@ant-design/icons";
import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Button, Divider, Space, Typography } from "antd";
import { FC, ReactNode } from "react";
import { useNavigate } from "react-router-dom";

export const SignAsOther: FC<{ tips: ReactNode; waitlist?: boolean }> = ({
  tips,
  waitlist = false,
}) => {
  const navigate = useNavigate();
  const profileService = useInject(ProfileService);
  return (
    <CenterBox>
      {tips}
      {profileService.profile?.oauth?.id ? (
        <>
          <Typography.Paragraph>
            You are logged in as{" "}
            <strong>{profileService.profile?.oauth?.email}</strong>
          </Typography.Paragraph>
          <Space direction="vertical">
            {waitlist && (
              <Button
                block
                type="primary"
                onClick={() => navigate("/waitlist", { relative: "route" })}
              >
                Join waitlist
              </Button>
            )}
            <Button
              block
              type="primary"
              onClick={() => navigate("/login", { relative: "route" })}
            >
              Sign in as a different user
            </Button>
          </Space>

          <Divider />
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
          <Divider />
        </>
      )}

      <div
        css={css`
          text-align: center;
        `}
      >
        <Space split={<Divider type="vertical" />}>
          <Button
            rel="noreferrer"
            href="https://www.lepton.ai"
            target="_blank"
            type="text"
            icon={<ReadOutlined />}
          />
          <Button
            type="text"
            rel="noreferrer"
            href="https://github.com/leptonai"
            target="_blank"
            icon={<GithubOutlined />}
          />
          <Button
            type="text"
            rel="noreferrer"
            href="https://twitter.com/leptonai"
            target="_blank"
            icon={<TwitterOutlined />}
          />
        </Space>
      </div>
    </CenterBox>
  );
};
