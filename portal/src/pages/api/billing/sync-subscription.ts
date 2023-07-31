import { updateSubscriptionItems } from "@/utils/stripe/update-subscription";
import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

// Sync all workspaces to the latest subscription
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const { data: workspaces } = await supabaseAdminClient
      .from("workspaces")
      .select("subscription_id");

    if (!workspaces || workspaces.length === 0) {
      res.status(412).send("No workspace found");
    } else {
      await Promise.all(
        workspaces.map(
          async (s) => await updateSubscriptionItems(s.subscription_id),
        ),
      );
      res.status(200).send("All workspace updated");
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
