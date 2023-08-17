import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";
import { Database } from "@/interfaces/database";

/**
 * @openapi
 * definitions:
 *   Workspace:
 *     type: object
 *     required: [id, url, token]
 *     properties:
 *       id:
 *         type: string
 *         description: Workspace ID
 *       url:
 *          type: string
 *          description: Workspace URL
 *       displayName:
 *         type: string
 *         description: Workspace display name
 *         nullable: true
 *       status:
 *         type: string
 *         description: Workspace status
 *         nullable: true
 *       paymentMethodAttached:
 *         type: boolean
 *         description: Workspace payment method attached
 *         nullable: true
 *         default: false
 *       token:
 *         type: string
 *         description: Workspace access token
 *         nullable: true
 *       tier:
 *          type: string
 *          description: Workspace tier
 *          enum: [Basic, Standard, Enterprise]
 */
interface Workspace {
  id: string;
  url: string | null;
  displayName: string | null;
  status: string | null;
  paymentMethodAttached: boolean;
  tier: "Basic" | "Standard" | "Enterprise";
  token: string;
}

interface ResponseError {
  error: string;
}

const nullity = <T>(value: T | null | undefined): value is null | undefined =>
  value === null || value === undefined;

/**
 * @openapi
 * /api/auth/workspaces:
 *   post:
 *     operationId: getAuthedWorkspaces
 *     summary: Get workspaces
 *     tags: [Auth]
 *     security:
 *       - cookieAuth:
 *         - user
 *     responses:
 *       200:
 *         description: Workspaces
 *         schema:
 *           type: array
 *           items:
 *             $ref: '#/definitions/Workspace'
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       500:
 *         description: Internal Server Error
 *         schema:
 *           $ref: '#/definitions/ResponseError'
 */
const workspaces: NextApiWithSupabaseHandler<
  Workspace[] | ResponseError
> = async (req, res, supabase) => {
  const { data, error } = await supabase.from("user_workspace").select(
    `
      token,
      workspaces(id, url, display_name, status, payment_method_attached, tier)
    `,
  );

  if (error) {
    res.statusMessage = error.message;
    return res.status(500).json({ error: error.message });
  }

  const workspaces = (data || [])
    .map((workspace) => {
      const getFieldValue = <
        T extends
          | "id"
          | "display_name"
          | "status"
          | "url"
          | "payment_method_attached"
          | "tier",
      >(
        field: T,
      ): Database["public"]["Tables"]["workspaces"]["Row"][T] => {
        const value = Array.isArray(workspace.workspaces)
          ? workspace.workspaces[0][field]
          : workspace.workspaces?.[field];
        return nullity(value) ? "" : value;
      };

      const id = getFieldValue("id");
      const displayName = getFieldValue("display_name");
      const paymentMethodAttached = getFieldValue("payment_method_attached");
      const status = getFieldValue("status");
      const url = getFieldValue("url");
      const tier = getFieldValue("tier") || "Basic";
      return {
        id,
        displayName,
        status,
        paymentMethodAttached,
        url,
        tier,
        token: workspace.token,
      };
    })
    .filter((workspace) => !!workspace.url);

  return res.json(workspaces);
};

export default withLogging(cors(serverClientWithAuthorized(workspaces)));
