import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import {
  AuthService,
  WaitlistEntry,
} from "@lepton-dashboard/services/auth.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";

import { Button, Col, Form, Input, Row, Select } from "antd";
import { FC, useState } from "react";

export const WaitList: FC = () => {
  useDocumentTitle("Join wait list");
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

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
    return <SignAsOther heading="Your account is now available" />;
  } else if (submitted || profileService.profile?.identification?.name) {
    return (
      <SignAsOther
        heading="You're on the waitlist!"
        tips=" Thank you for your interest"
      />
    );
  } else {
    return (
      <CenterBox>
        <Form
          css={css`
            text-align: initial;
          `}
          layout="horizontal"
          onFinish={onFinish}
        >
          <Form.Item name="name" rules={[{ required: true }]}>
            <Input autoFocus placeholder="Name*" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="company" rules={[{ required: true }]}>
                <Input placeholder="Company*" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role" rules={[{ required: true }]}>
                <Input placeholder="Role*" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="companySize">
                <Select
                  options={[
                    { label: "Micro (1-9)", value: "Micro (1-9)" },
                    { label: "Small (10-49)", value: "Small (10-49)" },
                    { label: "Medium (50-249)", value: "Medium (50-249)" },
                    { label: "Large (>249)", value: "Large (>249)" },
                  ]}
                  placeholder="Company Size"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="industry">
                <Input placeholder="Industry" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="workEmail"
            rules={[{ type: "email", message: "Please enter a valid email" }]}
          >
            <Input placeholder="Work Email" />
          </Form.Item>

          <Form.Item noStyle>
            <Button
              size="large"
              loading={loading}
              block
              type="primary"
              htmlType="submit"
            >
              Join waitlist
            </Button>
          </Form.Item>
        </Form>
      </CenterBox>
    );
  }
};
