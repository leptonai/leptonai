import type { GetServerSidePropsContext } from "next";
import Link from "next/link";
import {
  createPagesBrowserClient,
  createPagesServerClient,
  Session,
  User,
} from "@supabase/auth-helpers-nextjs";
import { Auth } from "@supabase/auth-ui-react";

const env = process.env.NODE_ENV;

const domain = env === "production" ? ".lepton.ai" : "localhost";

const redirectTo =
  env === "production"
    ? "https://portal.lepton.ai/api/auth/callback"
    : "http://localhost:8000/api/auth/callback";

export default function Login({
  user,
  session,
}: {
  user: User | null;
  session: Session | null;
}) {
  const supabase = createPagesBrowserClient({
    cookieOptions: {
      domain,
      maxAge: `${100 * 365 * 24 * 60 * 60}`,
      path: "/",
      sameSite: "Lax",
      secure: "secure",
    },
  });

  return session ? (
    <>
      <p>
        <Link href="/api/auth/profile">getServerSideProps</Link>
      </p>
      <p>user:</p>
      <pre>{JSON.stringify(session, null, 2)}</pre>
      <p>client-side data fetching with RLS</p>
      <pre>{JSON.stringify(user, null, 2)}</pre>
    </>
  ) : (
    <Auth
      onlyThirdPartyProviders
      providers={["google", "github"]}
      redirectTo={redirectTo}
      supabaseClient={supabase}
      localization={{
        variables: {
          sign_in: {
            social_provider_text: "Continue with {{provider}}",
          },
        },
      }}
    />
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
