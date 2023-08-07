import { supabaseAdminClient } from "@/utils/supabase";
import { SupabaseClient } from "@supabase/supabase-js";
import { Database } from "@/interfaces/database";

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

export async function updateWorkspaceByConsumerId(
  consumerId: string,
  data: Partial<Database["public"]["Tables"]["workspaces"]["Row"]>,
  supabaseClient: SupabaseClient,
) {
  return supabaseClient
    .from("workspaces")
    .update(data)
    .eq("consumer_id", consumerId);
}

export async function getWorkspaceById(
  id: string,
  supabaseClient: SupabaseClient,
): Promise<{
  id: string;
  created_at: string;
  consumer_id: string;
  coupon_id?: string;
  subscription_id: string;
  display_name: string;
  type: string;
} | null> {
  if (
    process.env.NODE_ENV === "development" &&
    process.env.SUPABASE_SECRET_KEY
  ) {
    return await getWorkspace(id, supabaseAdminClient);
  }
  return await getWorkspace(id, supabaseClient);
}
