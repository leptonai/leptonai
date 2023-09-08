# Portal Admin

All interface calls require the use of LEPTON_API_SECRET, which can be found in 1Password.

## Update products to all workspaces

When we add a new product and need to update the subscriptions of all workspaces. The current interface will
automatically add subscriptions for new products and keep existing subscriptions unchanged.

> The current product list: `src/utils/stripe/available-products.ts`

```http request
POST https://portal.lepton.ai/api/admin/update-workspace-product?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json
```

## Waive workspace

When workspace have unpaid invoices, and we hope to waive all invoices for them.

```http request
POST https://portal.lepton.ai/api/admin/waive-workspace?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "workspace_id": "y90kazsl",
}
```

## Update workspace tier

When we need to change workspace tier.

`tier` could be `Basic`, `Standard` or `Enterprise`.

```http request
POST https://portal.lepton.ai/api/admin/update-workspace-tier?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "workspace_id": "y90kazsl",
  "tier": "Standard"
}

```

## Update workspace coupon

When we need to issue discounts coupons to customers.

> Note: these coupons will be granted for each month, and immediately take effect when calling the api.
> When a new coupon is assigned, the old coupon will automatically become invalid.

`coupon` could be `0`, `10`, `100`, `500` or `1000`, when pass `0`, it means remove the workspace coupon.

```http request
POST https://portal.lepton.ai/api/admin/update-workspace-coupon?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "workspace_id": "y90kazsl",
  "coupon": "10"
}

```

## Reset workspace subscription

Reset all stripe customer and subscription related to the workspace.

> `chargeable` represents whether the current workspace is being charged in the Stripe production environment.

```http request
POST https://portal.lepton.ai/api/admin/reset-workspace-subscription?LEPTON_API_SECRET=${LEPTON_API_SECRET}
Content-Type: application/json

{
  "workspace_id": "y90kazsl",
  "chargeable": true
}
```
