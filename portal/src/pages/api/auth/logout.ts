import { NextApiHandler } from "next";
import { cors } from "@/utils/cors";
import { createPagesServerClientWithCookieOptions } from "@/utils/supabase";

const logout: NextApiHandler = async (req, res) => {
  const supabase = createPagesServerClientWithCookieOptions(req, res, true);

  await supabase.auth.signOut();

  const next = req.query.next;

  if (typeof next === "string") {
    res.redirect(`/login?next=${next}`);
    return;
  }

  res.redirect("/login");
};

export default cors(logout);
