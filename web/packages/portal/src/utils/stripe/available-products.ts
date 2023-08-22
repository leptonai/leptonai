import Stripe from "stripe";

export const AvailableProducts: Stripe.SubscriptionCreateParams.Item[] = [
  {
    price: "price_1NVbn2BcUfXYxWWViU0XrNgA",
    metadata: { shape: "cpu.small" },
  },
  {
    price: "price_1NVbnlBcUfXYxWWVpXUeFNnl",
    metadata: { shape: "cpu.medium" },
  },
  {
    price: "price_1NVboUBcUfXYxWWVLB9kZXzA",
    metadata: { shape: "cpu.large" },
  },
  {
    price: "price_1NVbpbBcUfXYxWWVTfS6a74e",
    metadata: { shape: "gpu.t4" },
  },
  {
    price: "price_1NVbqXBcUfXYxWWVVQRL3Gl3",
    metadata: { shape: "gpu.a10" },
  },
  {
    price: "price_1NVbrIBcUfXYxWWVk7G25XEB",
    metadata: { shape: "gpu.a100" },
  },
  {
    price: "price_1NZmG4BcUfXYxWWVuAfTMmpY",
    metadata: { shape: "storage" },
  },
];
