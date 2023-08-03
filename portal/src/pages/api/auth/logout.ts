import { NextApiHandler } from "next";
import { cors } from "@/utils/cors";
import { createPagesServerClientWithCookieOptions } from "@/utils/supabase";

const logout: NextApiHandler = async (req, res) => {
  const supabase = createPagesServerClientWithCookieOptions(req, res, true);

  await supabase.auth.signOut();

  res.setHeader("Set-Cookie", [
    ...(res.getHeader("Set-Cookie") as string[]),
    // Remove cookies from previous versions
    `sb-oauth-auth-token-code-verifier=; Max-Age=0; Domain=${req.headers.host}; Path=/;`,
    `sb-oauth-auth-token=; Max-Age=0; Domain=${req.headers.host}; Path=/;`,
    `sb-oauth-auth-token-code-verifier=; Max-Age=0; Path=/;`,
    `sb-oauth-auth-token=; Max-Age=0; Path=/;`,
  ]);

  const next = req.query.next;

  if (typeof next === "string") {
    res.redirect(`/login?next=${next}`);
    return;
  }

  res.redirect("/login");
};

export default cors(logout);
