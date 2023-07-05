import { css } from "@emotion/react";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { Typography } from "antd";
import { FC } from "react";

export const Policies: FC = () => {
  return (
    <div
      css={css`
        flex: 0 0 auto;
        text-align: center;
        margin-top: 12px;
      `}
    >
      <ThemeProvider token={{ fontSize: 12 }}>
        <Typography.Text>
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
        </Typography.Text>
      </ThemeProvider>
    </div>
  );
};
