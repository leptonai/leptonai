import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { OAuthLogin } from "@lepton-dashboard/routers/login/components/oauth-login";
import { TokenLogin } from "@lepton-dashboard/routers/login/components/token-login";
import { useInject } from "@lepton-libs/di";
import { css } from "@emotion/react";
import { Divider, Typography } from "antd";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";

export const Login = () => {
  const authService = useInject(AuthService);
  useDocumentTitle("Login");
  return (
    <CenterBox>
      <div
        css={css`
          flex: 1 1 auto;
          display: flex;
          align-items: center;
          justify-content: center;
        `}
      >
        <div
          css={css`
            flex: 1 1 auto;
          `}
        >
          {authService.client ? (
            <OAuthLogin client={authService.client} />
          ) : (
            <TokenLogin />
          )}
        </div>
      </div>
      <div
        css={css`
          flex: 0 0 auto;
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
    </CenterBox>
  );
};
