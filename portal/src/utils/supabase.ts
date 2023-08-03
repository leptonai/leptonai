import { createClient, Session, SupabaseClient } from "@supabase/supabase-js";
import { NextApiHandler, NextApiRequest, NextApiResponse } from "next";
import { createPagesServerClient } from "@supabase/auth-helpers-nextjs";

// Caution: this is the admin supabase client, should not expose it directly
export const supabaseAdminClient = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  process.env.SUPABASE_SECRET_KEY || "invalid",
  {
    auth: {
      persistSession: false,
    },
  },
);

export const getCookieOptions = (domainUrl: URL | string, clear = false) => {
  const normalizedDomain =
    typeof domainUrl === "string" ? domainUrl : domainUrl.hostname;
  const preview = /^.+-leptonai\.vercel\.app$/i.test(normalizedDomain);
  const domain =
    normalizedDomain === "localhost"
      ? "localhost"
      : preview
      ? normalizedDomain
      : ".lepton.ai";
  // 10 minutes for preview, 100 years for production
  const maxAge = preview ? 60 * 10 : 100 * 365 * 24 * 60 * 60;
  return {
    domain,
    maxAge: clear ? 0 : maxAge,
    path: "/",
    sameSite: preview ? "None" : "Lax",
    secure: "Strict",
  };
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type NextApiWithSupabaseHandler<T = any> = (
  req: NextApiRequest,
  res: NextApiResponse<T>,
  supabase: SupabaseClient,
  session: Session,
) => unknown | Promise<unknown>;

export const createPagesServerClientWithCookieOptions = (
  req: NextApiRequest,
  res: NextApiResponse,
  clearCookies?: boolean,
) => {
  const domainUrl = new URL(`protocol://${req.headers.host}`);
  return createPagesServerClient(
    { req, res },
    {
      cookieOptions: getCookieOptions(domainUrl, clearCookies),
    },
  );
};

export const serverClientWithAuthorized =
  (fn: NextApiWithSupabaseHandler): NextApiHandler =>
  async (req: NextApiRequest, res: NextApiResponse) => {
    const supabase = createPagesServerClientWithCookieOptions(req, res);

    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.user) {
      // Auth condition not met, return 401.
      return res.status(401).json({ error: "Unauthorized" });
    }

    if (
      /^https:\/\/.+-leptonai\.vercel\.app$/i.test(req.headers.origin || "")
    ) {
      if (!session.user.email || !session.user.email.endsWith("@lepton.ai")) {
        return res.status(403).json({ error: "Forbidden" });
      }
    }

    return await fn(req, res, supabase, session);
  };
