import { Policies } from "@lepton-dashboard/components/policies";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { OAuthLogin } from "@lepton-dashboard/routers/login/components/oauth-login";
import { TokenLogin } from "@lepton-dashboard/routers/login/components/token-login";
import { useInject } from "@lepton-libs/di";
import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useSearchParams } from "react-router-dom";
import { useMemo } from "react";

function getURL(url: string | null): URL;
function getURL(url: string | null, fallback: URL): URL;
function getURL(url: string | null, fallback?: URL): null | URL {
  let parsedURL: URL | null;
  try {
    parsedURL = url ? new URL(decodeURIComponent(url)) : null;
  } catch (e) {
    parsedURL = null;
  }
  if (
    parsedURL &&
    (parsedURL.hostname === "localhost" ||
      parsedURL.hostname.endsWith("lepton.ai"))
  ) {
    return parsedURL;
  } else {
    return fallback || null;
  }
}

export const Login = () => {
  const authService = useInject(AuthService);
  const [params] = useSearchParams();
  const callbackURL = params.get("callbackURL");
  const redirectTo = params.get("redirectTo");
  useDocumentTitle("Login");

  const url = useMemo(() => {
    const parsedCallbackURL = getURL(
      callbackURL,
      new URL(window.location.origin)
    );
    const parsedRedirectTo = getURL(redirectTo);
    if (parsedRedirectTo) {
      const callbackURL = new URL(`${window.location.origin}/redirect`);
      callbackURL!.searchParams.set("to", parsedRedirectTo.toString());
      return callbackURL.toString();
    }
    return parsedCallbackURL.toString();
  }, [callbackURL, redirectTo]);

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
            <OAuthLogin url={url} client={authService.client} />
          ) : (
            <TokenLogin />
          )}
        </div>
      </div>
      <Policies />
    </CenterBox>
  );
};
