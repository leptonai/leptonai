import { css } from "@emotion/react";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { Divider, Typography } from "antd";
import { FC } from "react";

export const Policies: FC = () => {
  return (
    <div
      css={css`
        flex: 0 0 auto;
        text-align: center;
        margin-top: -8px;
      `}
    >
      <Divider />
      <ThemeProvider token={{ fontSize: 12 }}>
        <Typography.Paragraph>
          By continuing, you agree to{" "}
          <Typography.Link
            target="_blank"
            href="https://www.lepton.ai/policies/tos"
          >
            Lepton AI's Terms of Service
          </Typography.Link>{" "}
          and{" "}
          <Typography.Link
            target="_blank"
            href="https://www.lepton.ai/policies/privacy"
          >
            Privacy Policy
          </Typography.Link>
          .
        </Typography.Paragraph>
      </ThemeProvider>
    </div>
  );
};
