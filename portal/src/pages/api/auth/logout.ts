import { NextApiHandler } from "next";
import { createPagesServerClient } from "@supabase/auth-helpers-nextjs";
import { cors } from "@/utils/cors";

const logout: NextApiHandler = async (req, res) => {
  // Create authenticated Supabase Client
  const supabase = createPagesServerClient({ req, res });

  await supabase.auth.signOut();

  const next = req.query.next;

  if (typeof next === "string") {
    res.redirect(`/login?next=${next}`);
    return;
  }

  res.redirect("/login");
};

export default cors(logout);
