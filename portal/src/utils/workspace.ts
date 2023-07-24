import { supabase } from "@/utils/supabase";

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
  const accessToken = cookies[`lepton-access-token`];
  const refreshToken = cookies[`lepton-refresh-token`];

  if (!accessToken || !refreshToken) {
    return null;
  }

  await supabase.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  });

  const { data: workspaces } = await supabase
    .from("workspaces")
    .select()
    .eq("id", id);

  if (workspaces && workspaces.length) {
    return workspaces[0];
  } else {
    return null;
  }
}
