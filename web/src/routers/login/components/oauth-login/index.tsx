import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Auth } from "@supabase/auth-ui-react";
import { SupabaseClient } from "@supabase/supabase-js";
import { FC, useMemo } from "react";

export const OAuthLogin: FC<{ client: SupabaseClient }> = ({ client }) => {
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
  return (
    <div
      css={css`
        .supabase-auth-ui_ui-container {
          gap: 8px !important;
        }
      `}
    >
      <Auth
        onlyThirdPartyProviders
        providers={["google", "github"]}
        redirectTo={window.location.origin}
        supabaseClient={client}
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
  );
};
