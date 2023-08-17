import { NextApiHandler } from "next";
import { cors } from "@/utils/cors";
import { createPagesServerClientWithCookieOptions } from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * /api/auth/logout:
 *   get:
 *     operationId: logout
 *     summary: Logout
 *     description: |
 *       Remove authentication cookies and redirect to `/login` or the `next`
 *     tags: [Auth]
 *     parameters:
 *       - in: query
 *         name: next
 *         schema:
 *           type: string
 *           format: uri
 *         description: Redirect to this URL after logout
 *         required: false
 *     responses:
 *       304:
 *        description: |
 *           Remove authentication cookies and redirect to `/login` or the `next`
 *           query parameter
 *        headers:
 *           Set-Cookie:
 *             type: string
 *             description: sb-oauth-auth-token-code-verifier=; Max-Age=0; Path=/;
 */
const logout: NextApiHandler<void> = async (req, res) => {
  const supabase = createPagesServerClientWithCookieOptions(req, res);

  try {
    await supabase.auth.signOut();
  } catch (e) {
    console.error(e);
  }

  const cookies =
    typeof res.getHeader !== "function" ? [] : res.getHeader("Set-Cookie");
  const presetCookies = Array.isArray(cookies)
    ? cookies
    : cookies !== undefined
    ? [`${cookies}`]
    : [];

  res.setHeader("Set-Cookie", [
    ...presetCookies,
    // Remove cookies from previous versions
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

export default withLogging(cors(logout));
