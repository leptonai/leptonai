# Portal Admin

All interface calls require the use of LEPTON_API_SECRET, which can be found in 1Password.

## Sync subscription

When we add a new product and need to update the subscriptions of all workspaces. The current interface will automatically add subscriptions for new products and keep existing subscriptions unchanged.

> The current product list: `src/utils/stripe/available-products.ts`


```http request
POST https://portal.lepton.ai/api/admin/sync-subscription?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json
```

## Waive consumer

When users have unpaid invoices, and we hope to waive all invoices for them.

```http request
POST https://portal.lepton.ai/api/admin/waive-consumer?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "consumer_id": "cus_ONdxD138kkVAFU"
}
```

## Update subscription coupon

When we need to issue discounts coupons to customers.

> Note: these coupons will be valid for each cycle. When a new coupon is assigned, the old coupon will automatically become invalid.

coupon could be `10`, `100`, `500` or `1000`

```http request
POST https://portal.lepton.ai/api/admin/update-subscription-coupon?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "subscription_id": "sub_1NasgNBcUfXYxWWVYOy80jku",
  "coupon": "10"
}

```
