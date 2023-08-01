import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";

const workspaces: NextApiWithSupabaseHandler = async (req, res, supabase) => {
  const { data, error } = await supabase.from("user_workspace").select(
    `
      token,
      workspaces(id, url, display_name, status)
    `,
  );

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  const workspaces = (data || [])
    .map((workspace) => {
      const getFieldValue = <
        T extends "id" | "display_name" | "status" | "url",
      >(
        field: T,
      ) => {
        const value = Array.isArray(workspace.workspaces)
          ? workspace.workspaces[0][field]
          : workspace.workspaces?.[field];
        return value ? value : "";
      };

      const id = getFieldValue("id");
      const displayName = getFieldValue("display_name");
      const status = getFieldValue("status");
      const url = getFieldValue("url");
      return {
        id,
        displayName,
        status,
        url,
        token: workspace.token,
      };
    })
    .filter((workspace) => !!workspace.url);

  return res.json(workspaces);
};

export default cors(serverClientWithAuthorized(workspaces));
