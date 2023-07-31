import { NextApiHandler } from "next";
import { createPagesServerClient } from "@supabase/auth-helpers-nextjs";
import { cors } from "@/utils/cors";

const profile: NextApiHandler = async (req, res) => {
  // Create authenticated Supabase Client
  const supabase = createPagesServerClient({ req, res });

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.user) {
    // Authentication successful, forward request to protected route.
    return res.json(session.user);
  }

  // Auth condition not met, return 401.
  return res.status(401).json({ error: "Unauthorized" });
};

export default cors(profile);
