import { supabase } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  try {
    const body = req.body;
    const id = body.id;
    const { data: workspaces } = await supabase
      .from("workspaces")
      .select("id, url")
      .eq("id", id);

    res
      .status(200)
      .json({ id: workspaces?.[0]?.id, url: workspaces?.[0]?.url });
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
