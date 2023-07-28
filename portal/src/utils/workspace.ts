import { supabaseAdminClient, supabaseClient } from "@/utils/supabase";
import { SupabaseClient } from "@supabase/supabase-js";

async function getWorkspace(id: string, client: SupabaseClient) {
  const { data: workspaces } = await client
    .from("workspaces")
    .select()
    .eq("id", id);

  if (workspaces && workspaces.length) {
    return workspaces[0];
  } else {
    return null;
  }
}

export async function getWorkspaceById(
  id: string,
  cookies: Partial<{
    [key: string]: string;
  }>,
): Promise<{
  id: string;
  created_at: string;
  consumer_id: string;
  subscription_id: string;
  display_name: string;
  type: string;
} | null> {
  if (process.env.NODE_ENV === "development") {
    return await getWorkspace(id, supabaseAdminClient);
  }

  const accessToken = cookies[`lepton-access-token`];
  const refreshToken = cookies[`lepton-refresh-token`];

  if (!accessToken || !refreshToken) {
    return null;
  }

  await supabaseClient.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  });

  return await getWorkspace(id, supabaseClient);
}
