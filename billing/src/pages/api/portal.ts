import { stripeClient } from "@/utils/stripe";
import { supabase } from "@/utils/supabase";
import { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  try {
    const workspaceId = JSON.parse(req.body).workspace_id;
    const accessToken = req.cookies[`lepton-access-token`];
    const refreshToken = req.cookies[`lepton-refresh-token`];

    if (!accessToken || !refreshToken) {
      return res.status(401).send("You are not authorized to call this API");
    }

    await supabase.auth.setSession({
      access_token: accessToken,
      refresh_token: refreshToken,
    });

    const { data: workspaces } = await supabase
      .from("workspaces")
      .select()
      .eq("id", workspaceId);

    if (!workspaces || workspaces.length === 0) {
      return res.status(401).send("You are not authorized to call this API");
    } else {
      const consumerId = workspaces[0].consumer_id;
      const session = await stripeClient.billingPortal.sessions.create({
        customer: consumerId,
        return_url: "https://dashboard.lepton.ai/settings/usage",
      });
      res.status(200).json({ url: session.url });
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
