import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * definitions:
 *   User:
 *     type: object
 *     required:
 *       - id
 *       - email
 *       - enable
 *       - metadata
 *       - role
 *       - last_sign_in_at
 *     properties:
 *       id:
 *         type: string
 *         description: User ID
 *       email:
 *         type: string
 *         description: User email
 *       enable:
 *         type: boolean
 *         description: User is enabled
 *       name:
 *         type: string
 *         description: User name
 *         nullable: true
 *       last_sign_in_at:
 *         type: string
 *         description: Last sign in at
 *         nullable: true
 *         format: date-time
 *       phone:
 *         type: string
 *         description: User phone number
 *         nullable: true
 *       role:
 *         type: string
 *         description: User role
 *         nullable: true
 *       metadata:
 *         type: object
 *         description: User metadata
 *         nullable: true
 *         additionalProperties: true
 */
interface User {
  id: string;
  email: string;
  enable: boolean;
  name: string | null;
  last_sign_in_at: string | undefined;
  phone: string | undefined;
  metadata: Record<string, unknown>;
  role: string | undefined;
}

interface ResponseError {
  error: string;
}

/**
 * @openapi
 * /api/auth/user:
 *   post:
 *     operationId: getUserInfo
 *     summary: Get user information
 *     tags: [Auth]
 *     security:
 *       - cookieAuth:
 *         - user
 *     responses:
 *       200:
 *         description: User information
 *         schema:
 *           $ref: '#/definitions/User'
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       404:
 *         description: User not found
 *         schema:
 *           $ref: '#/definitions/ResponseError'
 *       500:
 *         description: Internal Server Error
 *         schema:
 *           $ref: '#/definitions/ResponseError'
 */
const user: NextApiWithSupabaseHandler<User | ResponseError> = async (
  _,
  res,
  supabase,
  session
) => {
  const { data, error } = await supabase
    .from("users")
    .select("id, email, enable, name")
    .eq("email", session.user.email)
    .single();

  if (error) {
    res.statusMessage = error.message;
    return res.status(500).json({ error: error.message });
  }

  if (!data) {
    return res.status(404).json({ error: "User not found" });
  }

  const user = {
    last_sign_in_at: session.user.last_sign_in_at,
    phone: session.user.phone,
    metadata: session.user.user_metadata,
    role: session.user.role,
    ...data,
  };

  return res.json(user);
};

export default withLogging(cors(serverClientWithAuthorized(user)));
