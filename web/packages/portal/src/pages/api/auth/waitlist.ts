import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * definitions:
 *   WaitlistEntry:
 *     type: object
 *     required:
 *       - name
 *       - company
 *       - role
 *     properties:
 *       name:
 *         type: string
 *         description: Full name
 *       company:
 *         type: string
 *         description: Company name
 *       role:
 *         type: string
 *         description: Role
 *       company_size:
 *         type: string
 *         description: Company size
 *       industry:
 *         type: string
 *         description: Industry
 *       work_email:
 *         type: string
 *         description: Work email
 *         format: email
 */
interface WaitlistEntry {
  name: string;
  company: string;
  role: string;
  company_size: string;
  industry: string;
  work_email: string;
}

interface ResponseError {
  error: string;
}

/**
 * @openapi
 * /api/auth/waitlist:
 *   post:
 *     operationId: joinWaitlist
 *     summary: Join waitlist
 *     tags: [Auth]
 *     security:
 *       - cookieAuth:
 *         - user
 *     parameters:
 *       - in: body
 *         name: body
 *         description: Waitlist entry
 *         required: true
 *         schema:
 *           $ref: '#/definitions/WaitlistEntry'
 *     responses:
 *       200:
 *         description: Waitlist entry
 *       405:
 *         description: Method not allowed
 *         schema:
 *           type: string
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       500:
 *         description: Internal server Error
 *         schema:
 *           $ref: '#/definitions/ResponseError'
 */
const waitlist: NextApiWithSupabaseHandler<null | ResponseError> = async (
  req,
  res,
  supabase
) => {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  const body: WaitlistEntry = req.body;

  const { data = null, error } = await supabase.rpc("join_waitlist", {
    name: body.name,
    company: body.company,
    role: body.role,
    company_size: body.company_size || "",
    industry: body.industry || "",
    work_email: body.work_email || "",
  });

  if (error) {
    res.statusMessage = error.message;
    return res.status(500).json({ error: error.message });
  }

  return res.json(data);
};

export default withLogging(cors(serverClientWithAuthorized(waitlist)));
