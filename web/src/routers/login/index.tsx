import { Auth } from "@supabase/auth-ui-react";
import styled from "@emotion/styled";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { LeptonFillIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { TitleService } from "@lepton-dashboard/services/title.service";
import { useEffect } from "react";
import { AuthService } from "@lepton-dashboard/services/auth.service";

const Container = styled.div`
  height: 100%;
  overflow: auto;
  padding-top: 256px;
`;

const LoginContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 300px;
  margin: 0 auto;
`;

const Logo = styled.h2`
  display: flex;
  align-items: center;
  justify-content: center;
`;

const Text = styled.span`
  margin-left: 8px;
`;

export const Login = () => {
  const titleService = useInject(TitleService);
  const authService = useInject(AuthService);
  useEffect(() => {
    titleService.setTitle("Login");
  }, [titleService]);

  const theme = useAntdTheme();
  const customTheme = {
    default: {
      colors: {
        brand: "#2D9CDB",
        brandAccent: "#41b0f3",
        brandButtonText: theme.colorWhite,
      },
    },
  };

  if (!authService.client) return null;

  return (
    <Container>
      <LoginContainer>
        <Logo>
          <LeptonFillIcon />
          <Text>Lepton AI</Text>
        </Logo>
        <Auth
          onlyThirdPartyProviders
          providers={["google", "github"]}
          redirectTo={window.location.origin}
          supabaseClient={authService.client}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: customTheme.default.colors,
              },
            },
          }}
        />
      </LoginContainer>
    </Container>
  );
};
