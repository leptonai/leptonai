import { Auth } from "@supabase/auth-ui-react";
import { useInject } from "@lepton-libs/di";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { useEffect, useMemo } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { Divider, Typography } from "antd";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";

export const Login = () => {
  const titleService = useInject(TitleService);
  const authService = useInject(AuthService);
  const theme = useAntdTheme();
  const appearance = useMemo(() => {
    return {
      variables: {
        default: {
          colors: {
            brand: "#2F80ED",
            brandAccent: "#2D9CDB",
            brandButtonText: "white",
            defaultButtonBackground: "#000",
            defaultButtonBackgroundHover: "#333",
            defaultButtonBorder: "transparent",
            defaultButtonText: "#fff",
            dividerBackground: theme.colorBorder,
            inputBackground: theme.colorBgLayout,
            inputBorder: theme.colorBorder,
            inputBorderHover: theme.colorBorderSecondary,
            inputBorderFocus: theme.colorBorderSecondary,
            inputText: theme.colorTextHeading,
            inputLabelText: theme.colorText,
            inputPlaceholder: theme.colorTextSecondary,
            messageText: theme.colorText,
            messageTextDanger: theme.colorError,
            anchorTextColor: theme.colorText,
            anchorTextHoverColor: theme.colorTextSecondary,
          },
          space: {
            spaceSmall: `${theme.paddingXL}px`,
            spaceMedium: `${theme.paddingXL}px`,
            spaceLarge: `${theme.paddingXL}px`,
            labelBottomMargin: `${theme.paddingXL}px`,
            anchorBottomMargin: `${theme.paddingXL}px`,
            emailInputSpacing: `${theme.paddingXL}px`,
            socialAuthSpacing: `${theme.paddingXL}px`,
            buttonPadding: "7px 15px",
            inputPadding: "8px 16px",
          },
          fontSizes: {
            baseBodySize: `${theme.fontSize}px`,
            baseInputSize: `${theme.fontSize}px`,
            baseLabelSize: `${theme.fontSize}px`,
            baseButtonSize: `14px`,
          },
          fonts: {
            bodyFontFamily: theme.fontFamily,
            buttonFontFamily: theme.fontFamily,
            inputFontFamily: theme.fontFamily,
            labelFontFamily: theme.fontFamily,
          },
          borderWidths: {
            buttonBorderWidth: "1px",
            inputBorderWidth: "1px",
          },
          radii: {
            borderRadiusButton: `${theme.borderRadius}px`,
            buttonBorderRadius: `${theme.borderRadius}px`,
            inputBorderRadius: `${theme.borderRadius}px`,
          },
        },
      },
    };
  }, [theme]);

  useEffect(() => {
    titleService.setTitle("Login");
  }, [titleService]);

  if (!authService.client)
    return (
      <CenterBox>
        <Typography.Title level={3}>
          Oauth is not enabled in current environment.
        </Typography.Title>
      </CenterBox>
    );

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
            .supabase-auth-ui_ui-container {
              gap: 8px !important;
            }
          `}
        >
          <Auth
            onlyThirdPartyProviders
            providers={["google", "github"]}
            redirectTo={window.location.origin}
            supabaseClient={authService.client}
            localization={{
              variables: {
                sign_in: {
                  social_provider_text: "Continue with {{provider}}",
                },
              },
            }}
            appearance={appearance}
          />
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
          <Typography.Paragraph
            css={css`
              font-family: ${theme.fontFamily};
            `}
          >
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
