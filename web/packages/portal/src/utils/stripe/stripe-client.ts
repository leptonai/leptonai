import Stripe from "stripe";

const prodStripeClient = new Stripe(process.env.STRIPE_PROD_SECRET_KEY!, {
  apiVersion: "2022-11-15",
});

const testStripeClient = new Stripe(process.env.STRIPE_TEST_SECRET_KEY!, {
  apiVersion: "2022-11-15",
});

export const getStripeClient = (chargeable: boolean) => {
  return chargeable ? prodStripeClient : testStripeClient;
};
