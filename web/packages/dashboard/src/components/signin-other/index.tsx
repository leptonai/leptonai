import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Button, Col, Row, Typography } from "antd";
import { FC, ReactNode } from "react";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

export const SignAsOther: FC<{
  heading?: string;
  tips?: string;
  buttons?: ReactNode;
}> = ({ heading, tips, buttons }) => {
  const navigateService = useInject(NavigateService);
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  return (
    <CenterBox>
      {heading && (
        <Typography.Title
          level={2}
          css={css`
            margin-top: 0;
          `}
        >
          {heading}
        </Typography.Title>
      )}
      {tips && <Typography.Paragraph>{tips}</Typography.Paragraph>}
      {authService.authServerUrl ? (
        <>
          <Typography.Paragraph>
            You are logged in as{" "}
            <strong>{profileService.profile?.identification?.email}</strong>
          </Typography.Paragraph>
          <Row gutter={[16, 16]}>
            {buttons}
            <Col flex={1}>
              <Button
                block
                type="primary"
                onClick={() =>
                  authService.logout().subscribe(() =>
                    navigateService.navigateTo("login", {
                      relative: "route",
                    })
                  )
                }
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
            type="primary"
            onClick={() =>
              authService.logout().subscribe(() =>
                navigateService.navigateTo("login", {
                  relative: "route",
                })
              )
            }
          >
            Try a different token
          </Button>
        </>
      )}
    </CenterBox>
  );
};
