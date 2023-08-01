import { NextApiHandler } from "next";
import { createPagesServerClient } from "@supabase/auth-helpers-nextjs";

const callback: NextApiHandler = async (req, res) => {
  // Create authenticated Supabase Client
  const supabase = createPagesServerClient({ req, res });

  const code = req.query.code;
  const next = req.query.next;

  if (typeof code === "string") {
    await supabase.auth.exchangeCodeForSession(code);
  }

  if (typeof next === "string") {
    res.redirect(next);
    return;
  }

  if (process.env.NODE_ENV === "development") {
    res.redirect("http://localhost:3000");
    return;
  }

  res.redirect("/login");
};

export default callback;
