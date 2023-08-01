import { createClient, SupabaseClient, Session } from "@supabase/supabase-js";
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type NextApiWithSupabaseHandler<T = any> = (
  req: NextApiRequest,
  res: NextApiResponse<T>,
  supabase: SupabaseClient,
  session: Session,
) => unknown | Promise<unknown>;

export const serverClientWithAuthorized =
  (fn: NextApiWithSupabaseHandler): NextApiHandler =>
  async (req: NextApiRequest, res: NextApiResponse) => {
    const supabase = createPagesServerClient({ req, res });

    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.user) {
      // Auth condition not met, return 401.
      return res.status(401).json({ error: "Unauthorized" });
    }

    return await fn(req, res, supabase, session);
  };
