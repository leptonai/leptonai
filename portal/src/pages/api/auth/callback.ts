import { NextApiHandler } from "next";
import { createPagesServerClientWithCookieOptions } from "@/utils/supabase";

const callback: NextApiHandler = async (req, res) => {
  // Create authenticated Supabase Client
  const supabase = createPagesServerClientWithCookieOptions(req, res);

  const code = req.query.code;
  const next = req.query.next;

  if (typeof code === "string") {
    try {
      await supabase.auth.exchangeCodeForSession(code);
    } catch (error) {
      console.error(error);
    }
  }

  if (typeof next === "string") {
    res.redirect(next);
    return;
  }

  res.redirect("/login");
};

export default callback;
