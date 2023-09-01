import { Database } from "@lepton/database";
import Stripe from "stripe";

const AvailableProducts: Array<{
  test_price_id: string;
  prod_price_id: string;
  metadata: { shape?: string; tier?: Database["public"]["Enums"]["tier"] };
}> = [
  {
    prod_price_id: "price_1NkRpTBcUfXYxWWVL656v5xa",
    test_price_id: "price_1NkRdmBcUfXYxWWVLwtdWT8C",
    metadata: {
      tier: "Standard",
    },
  },
  {
    prod_price_id: "price_1NicCpBcUfXYxWWVJuS2SDxU",
    test_price_id: "price_1NVbn2BcUfXYxWWViU0XrNgA",
    metadata: { shape: "cpu.small" },
  },
  {
    prod_price_id: "price_1NicClBcUfXYxWWVTzdKsDkQ",
    test_price_id: "price_1NVbnlBcUfXYxWWVpXUeFNnl",
    metadata: { shape: "cpu.medium" },
  },
  {
    prod_price_id: "price_1NicCiBcUfXYxWWVaHCgh9As",
    test_price_id: "price_1NVboUBcUfXYxWWVLB9kZXzA",
    metadata: { shape: "cpu.large" },
  },
  {
    prod_price_id: "price_1NicCPBcUfXYxWWVmqqm5eIN",
    test_price_id: "price_1NVbpbBcUfXYxWWVTfS6a74e",
    metadata: { shape: "gpu.t4" },
  },
  {
    prod_price_id: "price_1NicCIBcUfXYxWWVj7IYK4MX",
    test_price_id: "price_1NVbqXBcUfXYxWWVVQRL3Gl3",
    metadata: { shape: "gpu.a10" },
  },
  {
    prod_price_id: "price_1NicCCBcUfXYxWWVxy7Xv3D6",
    test_price_id: "price_1NVbrIBcUfXYxWWVk7G25XEB",
    metadata: { shape: "gpu.a100" },
  },
  {
    prod_price_id: "price_1NicBTBcUfXYxWWVVmhC2ZGu",
    test_price_id: "price_1NZmG4BcUfXYxWWVuAfTMmpY",
    metadata: { shape: "storage" },
  },
  {
    prod_price_id: "price_1NlOInBcUfXYxWWVEyLHzwXE",
    test_price_id: "price_1NlOEwBcUfXYxWWVmW2ntSXj",
    metadata: { shape: "tuna.medium" },
  },
];

export const getAvailableProducts = (
  chargeable: boolean,
  tier: Database["public"]["Enums"]["tier"] | null
): Stripe.SubscriptionCreateParams.Item[] => {
  return AvailableProducts.map(
    ({ prod_price_id, test_price_id, metadata }) => ({
      price: chargeable ? prod_price_id : test_price_id,
      metadata,
    })
  ).filter((i) => {
    if (i.metadata.shape) {
      return true;
    } else {
      return i.metadata.tier === tier;
    }
  });
};