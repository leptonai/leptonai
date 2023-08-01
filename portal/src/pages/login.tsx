import type { GetServerSidePropsContext } from "next";
import Link from "next/link";
import {
  createPagesBrowserClient,
  createPagesServerClient,
  Session,
  User,
} from "@supabase/auth-helpers-nextjs";
import { Auth } from "@supabase/auth-ui-react";
import { useRouter } from "next/router";
import { useEffect, useMemo } from "react";
import { isDev, isProd } from "@/utils/env";
import { Logo } from "@/components/Logo";
import { Book, LogoGithub } from "@carbon/icons-react";
import Head from "next/head";
const domain = isProd ? ".lepton.ai" : "localhost";

const serverCallback = isProd
  ? "https://portal.lepton.ai/api/auth/callback"
  : "http://localhost:8000/api/auth/callback";

const validateNext = (next: string | string[] | undefined): string => {
  const defaultNext = isProd
    ? "https://dashboard.lepton.ai"
    : "http://localhost:3000";
  const url = Array.isArray(next) ? next[0] : next;
  if (!url) return defaultNext;
  try {
    const parsedURL = new URL(url);
    const allowedHosts = [
      "lepton.ai",
      "portal.lepton.ai",
      "dashboard.lepton.ai",
    ];
    if (isDev) {
      allowedHosts.push("localhost");
    }
    if (allowedHosts.includes(parsedURL.hostname)) {
      return url;
    } else {
      return defaultNext;
    }
  } catch {
    return defaultNext;
  }
};

export default function Login({
  user,
  session,
}: {
  user: User | null;
  session: Session | null;
}) {
  const router = useRouter();
  const { next } = router.query;
  const supabase = createPagesBrowserClient({
    cookieOptions: {
      domain,
      maxAge: `${100 * 365 * 24 * 60 * 60}`,
      path: "/",
      sameSite: "Lax",
      secure: "secure",
    },
  });

  const validatedNext = useMemo(() => validateNext(next), [next]);

  useEffect(() => {
    if (session && validatedNext && !isDev) {
      router.replace(validatedNext);
    }
  }, [session, validatedNext]);

  const redirectTo = useMemo(() => {
    const url = new URL(serverCallback);
    if (validatedNext && !isDev) {
      url.searchParams.set("next", validatedNext);
    }
    return url.toString();
  }, [validatedNext]);

  const appearance = useMemo(() => {
    return {
      extend: false,
      className: {
        container: "my-2 flex flex-col space-y-2",
        button:
          "p-2 flex items-center justify-center gap-2 rounded bg-black text-white text-sm",
      },
    };
  }, []);

  return (
    <div className="flex flex-1 flex-col overflow-hidden px-4 py-8 sm:px-6 lg:px-8">
      <Head>
        <title>Login | Lepton AI</title>
      </Head>
      {session ? (
        <>
          {isDev && (
            <>
              <p>
                <Link href={validatedNext}>next</Link>
                <br />
                <Link href="/api/auth/user">profile</Link>
                <br />
                <Link href="/api/auth/logout?next=https://dashboard.lepton.ai/">
                  logout
                </Link>
              </p>
              <p>session:</p>
              <pre>{JSON.stringify(session, null, 2)}</pre>
              <p>user:</p>
              <pre>{JSON.stringify(user, null, 2)}</pre>
            </>
          )}
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center pb-16 pt-12">
          <Logo className="h-7" />
          <div className="w-full max-w-sm flex items-center justify-center p-8 m-7 border-y border-gray-800">
            <div className="w-full max-w-xs">
              <Auth
                onlyThirdPartyProviders
                providers={["google", "github"]}
                redirectTo={redirectTo}
                supabaseClient={supabase}
                appearance={appearance}
                localization={{
                  variables: {
                    sign_in: {
                      social_provider_text: "Continue with {{provider}}",
                    },
                  },
                }}
              />
              <p className="text-center text-xs	mt-6 leading-6">
                By continuing, you agree to&nbsp;
                <a target="_blank" href="https://www.lepton.ai/policies/tos">
                  Lepton AI's Terms of Service
                </a>
                &nbsp;and&nbsp;
                <a
                  target="_blank"
                  href="https://www.lepton.ai/policies/privacy"
                >
                  Privacy Policy
                </a>
                .
              </p>
            </div>
          </div>
          <div className="grid grid-cols-3 divide-x text-center">
            <div className="px-5">
              <a href="https://www.lepton.ai/" target="_blank">
                <Book size={20} />
              </a>
            </div>
            <div className="px-5">
              <a
                href="https://github.com/leptonai/"
                rel="noopener"
                target="_blank"
              >
                <LogoGithub size={20} />
              </a>
            </div>
            <div className="px-5">
              <a href="https://x.com/leptonai/" rel="noopener" target="_blank">
                <svg width="18" height="18" viewBox="0 -2 22 20">
                  <path d="M16.99 0H20.298L13.071 8.26L21.573 19.5H14.916L9.702 12.683L3.736 19.5H0.426L8.156 10.665L0 0H6.826L11.539 6.231L16.99 0ZM15.829 17.52H17.662L5.83 1.876H3.863L15.829 17.52Z"></path>
                </svg>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export const getServerSideProps = async (ctx: GetServerSidePropsContext) => {
  const supabase = createPagesServerClient(ctx);

  const {
    data: { session },
  } = await supabase.auth.getSession();

  return {
    props: {
      session,
      user: session?.user ?? null,
    },
  };
};
