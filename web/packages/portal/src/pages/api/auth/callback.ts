import { NextApiHandler } from "next";
import { createPagesServerClientWithCookieOptions } from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * /api/auth/callback:
 *   get:
 *     operationId: loginCallback
 *     summary: Callback for social login
 *     description: |
 *       This endpoint is called by the social login provider after the user has authenticated.
 *       It exchanges the authorization code for a session and sets the authentication cookies.
 *     tags: [Auth]
 *     parameters:
 *       - in: query
 *         name: code
 *         schema:
 *           type: string
 *         description: Authorization code from the social login provider
 *         required: true
 *       - in: query
 *         name: next
 *         schema:
 *           type: string
 *           format: uri
 *         description: Redirect to this URL after login
 *         required: false
 *     responses:
 *       304:
 *         description: |
 *           Set authentication cookies and redirect to `/login` or the `next`
 *         headers:
 *           Set-Cookie:
 *             type: string
 *             description: sb-oauth-auth-token=1234567890abcdef; Path=/; Secure; SameSite=Lax;
 */
const callback: NextApiHandler<void> = async (req, res) => {
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

export default withLogging(callback);
