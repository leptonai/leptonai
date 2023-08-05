import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";

const nullity = <T>(value: T | null | undefined): value is null | undefined =>
  value === null || value === undefined;

const workspaces: NextApiWithSupabaseHandler = async (req, res, supabase) => {
  const { data, error } = await supabase.from("user_workspace").select(
    `
      token,
      workspaces(id, url, display_name, status, payment_method_attached)
    `,
  );

  if (error) {
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
          | "payment_method_attached",
      >(
        field: T,
      ) => {
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
      return {
        id,
        displayName,
        status,
        paymentMethodAttached,
        url,
        token: workspace.token,
      };
    })
    .filter((workspace) => !!workspace.url);

  return res.json(workspaces);
};

export default cors(serverClientWithAuthorized(workspaces));
