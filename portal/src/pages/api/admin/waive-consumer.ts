import { stripeClient } from "@/utils/stripe/stripe-client";
import type { NextApiRequest, NextApiResponse } from "next";
import { withLogging } from "@/utils/logging";

// Waive all invoice under consumer
async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const consumerId = req.body.consumer_id;

    const { data: invoices } = await stripeClient.invoices.list({
      customer: consumerId,
      status: "open",
    });
    if (!invoices || invoices.length === 0) {
      res.status(412).send("No unpaid invoices found");
    } else {
      await Promise.all(
        invoices.map(
          async (s) =>
            await stripeClient.invoices.pay(s.id, { paid_out_of_band: true }),
        ),
      );
      res.status(200).send(`All invoices under ${consumerId} paid`);
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
}

export default withLogging(handler);
