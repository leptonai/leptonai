import { Policies } from "@lepton-dashboard/components/policies";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { TokenLogin } from "@lepton-dashboard/routers/login/components/token-login";
import { useInject } from "@lepton-libs/di";
import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useSearchParams } from "react-router-dom";
import { useEffect, useMemo } from "react";

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
  const next = params.get("next");
  useDocumentTitle("Login");

  const url = useMemo(() => {
    const parsedCallbackURL = getURL(next, new URL(window.location.origin));
    return parsedCallbackURL.toString();
  }, [next]);

  useEffect(() => {
    if (authService.authServerUrl && url) {
      window.location.href = `${
        authService.authServerUrl
      }/login?next=${encodeURIComponent(url)}`;
    }
  }, [authService, url]);

  return (
    !authService.authServerUrl && (
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
            <TokenLogin />
          </div>
        </div>
        <Policies />
      </CenterBox>
    )
  );
};
