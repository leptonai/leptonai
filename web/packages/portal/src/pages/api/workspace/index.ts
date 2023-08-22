import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiHandler } from "next";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * definitions:
 *   WorkspaceInfo:
 *     type: object
 *     required: [id, url, display_name]
 *     properties:
 *       id:
 *         type: string
 *         description: Workspace ID
 *       url:
 *         type: string
 *         nullable: true
 *         description: Workspace URL
 *       display_name:
 *         type: string
 *         nullable: true
 *         description: Workspace display name
 */
interface WorkspaceInfo {
  id: string;
  url: string | null;
  display_name: string | null;
}

/**
 * @openapi
 * /api/workspace:
 *   get:
 *     operationId: getWorkspace
 *     summary: Get a workspace information
 *     tags: [Workspace]
 *     parameters:
 *       - in: query
 *         name: id
 *         description: Workspace ID
 *         required: true
 *         schema:
 *          type: string
 *     responses:
 *       200:
 *         description: Workspace information
 *         schema:
 *           $ref: '#/definitions/WorkspaceInfo'
 *       500:
 *         description: Internal server error
 *         schema:
 *           type: string
 */
const handler: NextApiHandler<WorkspaceInfo | string> = async (req, res) => {
  try {
    const body = req.body;
    const id = body.id;
    const { data: workspaces } = await supabaseAdminClient
      .from("workspaces")
      .select("id, url, display_name")
      .eq("id", id);

    const workspace = workspaces?.[0];

    res.status(200).json(workspace!);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(handler);
