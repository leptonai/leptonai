import { Policies } from "@lepton-dashboard/components/policies";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { OAuthLogin } from "@lepton-dashboard/routers/login/components/oauth-login";
import { TokenLogin } from "@lepton-dashboard/routers/login/components/token-login";
import { useInject } from "@lepton-libs/di";
import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useSearchParams } from "react-router-dom";

export const Login = () => {
  const authService = useInject(AuthService);
  const [params] = useSearchParams();
  const callbackURL = params.get("callbackURL") || window.location.origin;
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
            <OAuthLogin url={callbackURL} client={authService.client} />
          ) : (
            <TokenLogin />
          )}
        </div>
      </div>
      <Policies />
    </CenterBox>
  );
};
