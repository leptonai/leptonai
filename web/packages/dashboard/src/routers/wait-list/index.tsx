import { css } from "@emotion/react";
import { LeptonIcon } from "@lepton-dashboard/components/icons";
import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { useInject } from "@lepton-libs/di";

import { Button, Col, Form, Input, Row, Select, Typography } from "antd";
import { FC, useMemo, useState } from "react";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { WaitlistEntry } from "@lepton-dashboard/interfaces/user";

export const WaitList: FC = () => {
  useDocumentTitle("Join wait list");
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  const navigateService = useInject(NavigateService);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const theme = useAntdTheme();
  const themeService = useInject(ThemeService);

  const background = useMemo(() => {
    if (themeService.getValidTheme() === "dark") {
      return "url(\"data:image/svg+xml,<svg id='patternId' width='100%' height='100%' xmlns='http://www.w3.org/2000/svg'><defs><pattern id='a' patternUnits='userSpaceOnUse' width='100' height='100' patternTransform='scale(3) rotate(70)'><rect x='0' y='0' width='100%' height='100%' fill='hsla(225,59.3%,10.6%,1)'/><path d='m33.64 0-.17.25h-33L4.3 6h33.07l4-6zm8.33 0-4.33 6.5h-33l3.83 5.75h33.06L49.7 0zm8.34 0-8.5 12.75h-33l3.83 5.75H45.7L58.03 0zm8.33 0L45.97 19h-33l3.83 5.75h33.06L66.36 0zm-8.5 25.25L33.63 50l3.86 5.8L54.03 31h33l-3.83-5.75zm4.16 6.25L37.8 56.25l3.87 5.8 16.53-24.8h33l-3.84-5.75zm4.17 6.25L41.97 62.5l3.86 5.8 16.54-24.8h33l-3.84-5.75zM62.63 44l-16.5 24.75 3.87 5.8 16.53-24.8h33L95.7 44zM100 50.45l-3.87 5.8 3.87 5.81v-11.6zM0 50.46v11.6L12.5 80.8l3.86-5.8zm95.83 6.25-3.87 5.8L100 74.55v-11.6zm-4.17 6.24-3.86 5.8 12.2 18.3v-11.6zM0 62.96v11.6l8.33 12.49 3.86-5.8zm87.5 6.24L83.63 75 100 99.54V87.96zM50 75.45 33.64 100h7.72l12.5-18.75zm-50 0v11.6l4.16 6.24 3.87-5.8zm54.17 6.25L41.97 100h7.73l8.33-12.5zm4.17 6.25L50.3 100h7.73l4.17-6.25zM0 87.95v11.59l3.86-5.8zm62.5 6.25-3.87 5.8h7.73z'  stroke-width='1' stroke='none' fill='hsla(225,39.8%,18.2%,1)'/><path d='M66.8.25 62.97 6h33l4.03 6.05V.45l-.14-.2zM0 .45v11.61L12.5 30.8l3.86-5.8zM62.63 6.5l-3.83 5.75h33l8.2 12.3v-11.6L95.7 6.5zm-4.16 6.25-3.84 5.75h33L100 37.06v-11.6l-8.47-12.71zM0 12.96v11.6l8.33 12.49 3.86-5.8zM54.3 19l-3.84 5.75h33L100 49.55l.01-.01V37.96L87.36 19zm-4.77 6.25H41.8L25.3 50l16.66 25-16.5 24.75h7.74L49.7 75 33.03 50zm-8.33 0h-7.74L16.96 50l16.67 25-16.5 24.75h7.73L41.36 75 24.7 50Zm-8.34 0h-7.73L8.63 50 25.3 75 8.8 99.75h7.73L33.03 75 16.36 50zm-16.07 0L.3 50l16.67 25L.46 99.75H8.2L24.7 75 8.02 50l16.5-24.75zM0 25.46v11.6l4.16 6.24 3.87-5.8zm0 12.5v11.58l3.86-5.79zm66.8 12.29L50.3 74.99l3.87 5.81 4.16 6.25 4.17 6.25 4.3 6.45h7.73L58.03 75l16.5-24.75zm16.06 0h-7.73L58.63 75l16.5 24.75h7.73L66.36 75zm.6 0L66.96 75l16.5 24.75h7.74L74.7 75l16.5-24.75zm16.07 0H91.8L75.3 75l16.5 24.75h7.73L83.03 75z'  stroke-width='1' stroke='none' fill='hsla(213,29.7%,32.4%,1)'/></pattern></defs><rect width='800%' height='800%' transform='translate(0,0)' fill='url(%23a)'/></svg>\")";
    } else {
      return "url(\"data:image/svg+xml,<svg id='patternId' width='100%' height='100%' xmlns='http://www.w3.org/2000/svg'><defs><pattern id='a' patternUnits='userSpaceOnUse' width='100' height='100' patternTransform='scale(3) rotate(155)'><rect x='0' y='0' width='100%' height='100%' fill='hsla(21,42.5%,64.5%,1)'/><path d='m33.64 0-.17.25h-33L4.3 6h33.07l4-6zm8.33 0-4.33 6.5h-33l3.83 5.75h33.06L49.7 0zm8.34 0-8.5 12.75h-33l3.83 5.75H45.7L58.03 0zm8.33 0L45.97 19h-33l3.83 5.75h33.06L66.36 0zm-8.5 25.25L33.63 50l3.86 5.8L54.03 31h33l-3.83-5.75zm4.16 6.25L37.8 56.25l3.87 5.8 16.53-24.8h33l-3.84-5.75zm4.17 6.25L41.97 62.5l3.86 5.8 16.54-24.8h33l-3.84-5.75zM62.63 44l-16.5 24.75 3.87 5.8 16.53-24.8h33L95.7 44zM100 50.45l-3.87 5.8 3.87 5.81v-11.6zM0 50.46v11.6L12.5 80.8l3.86-5.8zm95.83 6.25-3.87 5.8L100 74.55v-11.6zm-4.17 6.24-3.86 5.8 12.2 18.3v-11.6zM0 62.96v11.6l8.33 12.49 3.86-5.8zm87.5 6.24L83.63 75 100 99.54V87.96zM50 75.45 33.64 100h7.72l12.5-18.75zm-50 0v11.6l4.16 6.24 3.87-5.8zm54.17 6.25L41.97 100h7.73l8.33-12.5zm4.17 6.25L50.3 100h7.73l4.17-6.25zM0 87.95v11.59l3.86-5.8zm62.5 6.25-3.87 5.8h7.73z'  stroke-width='5' stroke='none' fill='hsla(26,100%,95.1%,1)'/><path d='M66.8.25 62.97 6h33l4.03 6.05V.45l-.14-.2zM0 .45v11.61L12.5 30.8l3.86-5.8zM62.63 6.5l-3.83 5.75h33l8.2 12.3v-11.6L95.7 6.5zm-4.16 6.25-3.84 5.75h33L100 37.06v-11.6l-8.47-12.71zM0 12.96v11.6l8.33 12.49 3.86-5.8zM54.3 19l-3.84 5.75h33L100 49.55l.01-.01V37.96L87.36 19zm-4.77 6.25H41.8L25.3 50l16.66 25-16.5 24.75h7.74L49.7 75 33.03 50zm-8.33 0h-7.74L16.96 50l16.67 25-16.5 24.75h7.73L41.36 75 24.7 50Zm-8.34 0h-7.73L8.63 50 25.3 75 8.8 99.75h7.73L33.03 75 16.36 50zm-16.07 0L.3 50l16.67 25L.46 99.75H8.2L24.7 75 8.02 50l16.5-24.75zM0 25.46v11.6l4.16 6.24 3.87-5.8zm0 12.5v11.58l3.86-5.79zm66.8 12.29L50.3 74.99l3.87 5.81 4.16 6.25 4.17 6.25 4.3 6.45h7.73L58.03 75l16.5-24.75zm16.06 0h-7.73L58.63 75l16.5 24.75h7.73L66.36 75zm.6 0L66.96 75l16.5 24.75h7.74L74.7 75l16.5-24.75zm16.07 0H91.8L75.3 75l16.5 24.75h7.73L83.03 75z'  stroke-width='5' stroke='none' fill='hsla(24,43.3%,76.5%,1)'/></pattern></defs><rect width='800%' height='800%' transform='translate(0,0)' fill='url(%23a)'/></svg>\")";
    }
  }, [themeService]);
  const onFinish = (values: WaitlistEntry) => {
    setLoading(true);
    authService.joinWaitlist(values).subscribe({
      next: () => {
        setSubmitted(true);
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    });
  };
  if (profileService.profile?.identification?.enable) {
    return (
      <SignAsOther
        buttons={
          <Col flex={1}>
            <Button
              block
              type="primary"
              onClick={() =>
                navigateService.navigateTo("root", { relative: "route" })
              }
            >
              Go to workspace
            </Button>
          </Col>
        }
        heading="Your account is now available"
      />
    );
  } else if (submitted || profileService.profile?.identification?.name) {
    return (
      <SignAsOther
        heading="You're on the waitlist!"
        tips=" Thank you for your interest"
      />
    );
  } else {
    return (
      <div
        css={css`
          height: 100%;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        `}
      >
        <div
          css={css`
            position: absolute;
            inset: 0;
            z-index: 0;
            background: ${theme.colorBgLayout};
            background-image: ${background};
          `}
        />
        <div
          css={css`
            width: 600px;
            background: ${theme.colorBgContainer};
            padding: 32px;
            position: relative;
            z-index: 1;
            box-shadow: ${theme.boxShadowTertiary};
            border-radius: ${theme.borderRadius}px;
          `}
        >
          <Typography.Title
            css={css`
              margin-top: 0;
            `}
            level={2}
          >
            <LeptonIcon />
            <span
              css={css`
                margin-left: 12px;
              `}
            >
              Join waitlist
            </span>
          </Typography.Title>
          <Form
            requiredMark={false}
            css={css`
              width: 100%;
              text-align: initial;
            `}
            initialValues={{
              companySize: "Micro (1-9)",
            }}
            layout="vertical"
            onFinish={onFinish}
          >
            <Form.Item name="name" label="Name" rules={[{ required: true }]}>
              <Input autoFocus />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="company"
                  label="Company"
                  rules={[{ required: true }]}
                >
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="role"
                  label="Role"
                  rules={[{ required: true }]}
                >
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="companySize" label="Company size">
              <Select
                options={[
                  { label: "Micro (1-9)", value: "Micro (1-9)" },
                  { label: "Small (10-49)", value: "Small (10-49)" },
                  { label: "Medium (50-249)", value: "Medium (50-249)" },
                  { label: "Large (>249)", value: "Large (>249)" },
                ]}
              />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="industry" label="Industry">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="workEmail"
                  label="Work email"
                  rules={[
                    { type: "email", message: "Please enter a valid email" },
                  ]}
                >
                  <Input />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item noStyle>
              <Button
                size="large"
                loading={loading}
                block
                type="primary"
                htmlType="submit"
              >
                Submit
              </Button>
            </Form.Item>
          </Form>
        </div>
      </div>
    );
  }
};
