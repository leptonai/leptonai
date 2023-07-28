import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  try {
    const body = req.body;
    const id = body.id;
    const { data: workspaces } = await supabaseAdminClient
      .from("workspaces")
      .select("id, url, display_name")
      .eq("id", id);

    const workspace = workspaces?.[0];

    res.status(200).json(workspace);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
