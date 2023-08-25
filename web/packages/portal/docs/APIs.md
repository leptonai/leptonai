# Portal API

## Version: 1.0.0

### Security

**cookieAuth**

| apiKey | _API Key_           |
| ------ | ------------------- |
| In     | cookie              |
| Name   | sb-oauth-auth-token |

**serverAuth**

| apiKey | _API Key_         |
| ------ | ----------------- |
| In     | query             |
| Name   | LEPTON_API_SECRET |

---

## Auth

Authentication APIs

### /api/auth/callback

#### GET

##### Summary

Callback for social login

##### Description

This endpoint is called by the social login provider after the user has authenticated.
It exchanges the authorization code for a session and sets the authentication cookies.

##### Parameters

| Name | Located in | Description                                       | Required | Schema       |
| ---- | ---------- | ------------------------------------------------- | -------- | ------------ |
| code | query      | Authorization code from the social login provider | Yes      | string       |
| next | query      | Redirect to this URL after login                  | No       | string (uri) |

##### Responses

| Code | Description                                                                                                                                                                            |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 304  | Set authentication cookies and redirect to `/login` or the `next` <br>**Headers:**<br>**Set-Cookie** (string): sb-oauth-auth-token=1234567890abcdef; Path=/; Secure; SameSite=Lax;<br> |

### /api/auth/logout

#### GET

##### Summary

Logout

##### Description

Remove authentication cookies and redirect to `/login` or the `next`

##### Parameters

| Name | Located in | Description                       | Required | Schema       |
| ---- | ---------- | --------------------------------- | -------- | ------------ |
| next | query      | Redirect to this URL after logout | No       | string (uri) |

##### Responses

| Code | Description                                                                                                                                                                                  |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 304  | Remove authentication cookies and redirect to `/login` or the `next` query parameter <br>**Headers:**<br>**Set-Cookie** (string): sb-oauth-auth-token-code-verifier=; Max-Age=0; Path=/;<br> |

### /api/auth/user

#### POST

##### Summary

Get user information

##### Responses

| Code | Description           | Schema                          |
| ---- | --------------------- | ------------------------------- |
| 200  | User information      | [User](#user)                   |
| 401  | Unauthorized          | string                          |
| 404  | User not found        | [ResponseError](#responseerror) |
| 500  | Internal Server Error | [ResponseError](#responseerror) |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| cookieAuth      | user   |

### /api/auth/waitlist

#### POST

##### Summary

Join waitlist

##### Parameters

| Name | Located in | Description    | Required | Schema                          |
| ---- | ---------- | -------------- | -------- | ------------------------------- |
| body | body       | Waitlist entry | Yes      | [WaitlistEntry](#waitlistentry) |

##### Responses

| Code | Description           | Schema                          |
| ---- | --------------------- | ------------------------------- |
| 200  | Waitlist entry        |                                 |
| 401  | Unauthorized          | string                          |
| 405  | Method not allowed    | string                          |
| 500  | Internal server Error | [ResponseError](#responseerror) |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| cookieAuth      | user   |

### /api/auth/workspaces

#### POST

##### Summary

Get workspaces

##### Responses

| Code | Description           | Schema                          |
| ---- | --------------------- | ------------------------------- |
| 200  | Workspaces            | [ [Workspace](#workspace) ]     |
| 401  | Unauthorized          | string                          |
| 500  | Internal Server Error | [ResponseError](#responseerror) |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| cookieAuth      | user   |

---

## Billing

Billing APIs

### /api/billing/invoice

#### POST

##### Summary

Get invoice data for a workspace

##### Parameters

| Name | Located in | Description  | Required | Schema                         |
| ---- | ---------- | ------------ | -------- | ------------------------------ |
| body | body       | Workspace ID | Yes      | { **"workspace_id"**: string } |

##### Responses

| Code | Description           | Schema              |
| ---- | --------------------- | ------------------- |
| 200  | Invoice data          | [Invoice](#invoice) |
| 401  | Unauthorized          | string              |
| 412  | Precondition failed   | string              |
| 500  | Internal server error | string              |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| cookieAuth      | user   |

### /api/billing/portal

#### POST

##### Summary

Get billing portal URL

##### Parameters

| Name | Located in | Description  | Required | Schema                         |
| ---- | ---------- | ------------ | -------- | ------------------------------ |
| body | body       | Workspace ID | Yes      | { **"workspace_id"**: string } |

##### Responses

| Code | Description           | Schema                      |
| ---- | --------------------- | --------------------------- |
| 200  | Billing portal URL    | { **"url"**: string (url) } |
| 401  | Unauthorized          | string                      |
| 412  | Precondition failed   | string                      |
| 500  | Internal server error | string                      |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| cookieAuth      | user   |

### /api/billing/report-compute

#### POST

##### Summary

Report compute usage to stripe

##### Parameters

| Name | Located in | Description  | Required | Schema                                            |
| ---- | ---------- | ------------ | -------- | ------------------------------------------------- |
| body | body       | Usage record | Yes      | [ReportComputeUsageBody](#reportcomputeusagebody) |

##### Responses

| Code | Description           | Schema                      |
| ---- | --------------------- | --------------------------- |
| 200  | The usage record      | [UsageRecord](#usagerecord) |
| 401  | Unauthorized          | string                      |
| 412  | Precondition failed   | string                      |
| 500  | Internal server error | string                      |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| serverAuth      | admin  |

### /api/billing/report-storage

#### POST

##### Summary

Report storage usage to stripe

##### Parameters

| Name | Located in | Description  | Required | Schema                                            |
| ---- | ---------- | ------------ | -------- | ------------------------------------------------- |
| body | body       | Usage record | Yes      | [ReportStorageUsageBody](#reportstorageusagebody) |

##### Responses

| Code | Description           | Schema                      |
| ---- | --------------------- | --------------------------- |
| 200  | The usage record      | [UsageRecord](#usagerecord) |
| 401  | Unauthorized          | string                      |
| 412  | Precondition failed   | string                      |
| 500  | Internal server error | string                      |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| serverAuth      | admin  |

### /api/billing/subscribe

#### POST

##### Summary

Subscribe a workspace to a plan

##### Parameters

| Name | Located in | Description         | Required | Schema |
| ---- | ---------- | ------------------- | -------- | ------ |
| body | body       | Subscription record | Yes      | object |

##### Responses

| Code | Description             | Schema |
| ---- | ----------------------- | ------ |
| 200  | The subscription record | object |
| 401  | Unauthorized            | string |
| 500  | Internal server error   | string |

##### Security

| Security Schema | Scopes |
| --------------- | ------ |
| serverAuth      | admin  |

### /api/billing/webhook

#### POST

##### Summary

Stripe webhook

##### Description

This endpoint is used by Stripe to send events to the server.

Events handled:

- `customer.subscription.updated`
  - Update workspace status based on subscription status
- `customer.subscription.created`
  - Update workspace status based on subscription status
- `payment_method.attached`
  - Update workspace payment_method_attached
- `payment_method.detached`
  - Update workspace payment_method_attached

##### Parameters

| Name             | Located in | Description                | Required | Schema |
| ---------------- | ---------- | -------------------------- | -------- | ------ |
| prod             | query      | is stripe prod env         | No       | string |
| stripe-signature | header     | The signature of the event | Yes      | string |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200  | Success     |        |

---

## Workspace

Workspace APIs

### /api/workspace

#### GET

##### Summary

Get a workspace information

##### Parameters

| Name | Located in | Description  | Required | Schema |
| ---- | ---------- | ------------ | -------- | ------ |
| id   | query      | Workspace ID | Yes      | string |

##### Responses

| Code | Description           | Schema                          |
| ---- | --------------------- | ------------------------------- |
| 200  | Workspace information | [WorkspaceInfo](#workspaceinfo) |
| 500  | Internal server error | string                          |

---

### Models

#### ResponseError

| Name  | Type   | Description   | Required |
| ----- | ------ | ------------- | -------- |
| error | string | Error message | No       |

#### User

| Name            | Type     | Description       | Required |
| --------------- | -------- | ----------------- | -------- |
| id              | string   | User ID           | Yes      |
| email           | string   | User email        | Yes      |
| enable          | boolean  | User is enabled   | Yes      |
| name            | string   | User name         | No       |
| last_sign_in_at | dateTime | Last sign in at   | Yes      |
| phone           | string   | User phone number | No       |
| role            | string   | User role         | Yes      |
| metadata        | object   | User metadata     | Yes      |

#### WaitlistEntry

| Name         | Type           | Description  | Required |
| ------------ | -------------- | ------------ | -------- |
| name         | string         | Full name    | Yes      |
| company      | string         | Company name | Yes      |
| role         | string         | Role         | Yes      |
| company_size | string         | Company size | No       |
| industry     | string         | Industry     | No       |
| work_email   | string (email) | Work email   | No       |

#### Workspace

| Name                  | Type    | Description                                                       | Required |
| --------------------- | ------- | ----------------------------------------------------------------- | -------- |
| id                    | string  | Workspace ID                                                      | Yes      |
| url                   | string  | Workspace URL                                                     | Yes      |
| displayName           | string  | Workspace display name                                            | No       |
| status                | string  | Workspace status                                                  | No       |
| paymentMethodAttached | boolean | Workspace payment method attached                                 | No       |
| token                 | string  | Workspace access token                                            | Yes      |
| tier                  | string  | Workspace tier<br>_Enum:_ `"Basic"`, `"Standard"`, `"Enterprise"` | No       |

#### Invoice

| Name           | Type                                         | Description                                                                                                                       | Required |
| -------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| open           | object                                       | Open [invoice](https://stripe.com/docs/api/invoices/object)                                                                       | Yes      |
| upcoming       | object                                       | Retrieve an [upcoming](https://stripe.com/docs/api/invoices/upcoming) invoice                                                     | Yes      |
| list           | [ object ]                                   | [Invoices](https://stripe.com/docs/api/invoices/list) for the subscription specified by `subscription_id` in the workspace record | Yes      |
| products       | [ object ]                                   | All active [products](https://stripe.com/docs/api/products/list) with their default prices and tiers                              | Yes      |
| coupon         | object                                       | [Coupon](https://stripe.com/docs/api/coupons/object) applied to the workspace                                                     | No       |
| current_period | { **"start"**: integer, **"end"**: integer } | Current period start and end dates                                                                                                | Yes      |

#### UsageRecord

A [usage record](https://stripe.com/docs/api/usage_records/object)

| Name        | Type   | Description                                                        | Required |
| ----------- | ------ | ------------------------------------------------------------------ | -------- |
| UsageRecord | object | A [usage record](https://stripe.com/docs/api/usage_records/object) |          |

#### ReportComputeUsageRecord

| Name         | Type     | Description                               | Required |
| ------------ | -------- | ----------------------------------------- | -------- |
| id           | string   |                                           | Yes      |
| workspace_id | string   | The workspace ID                          | Yes      |
| shape        | string   | The shape of the compute instance         | Yes      |
| usage        | float    | The usage quantity for the specified date | Yes      |
| end_time     | dateTime | The timestamp when this usage occurred    | Yes      |

#### ReportComputeUsageBody

| Name   | Type                                                  | Description             | Required |
| ------ | ----------------------------------------------------- | ----------------------- | -------- |
| record | [ReportComputeUsageRecord](#reportcomputeusagerecord) | The usage report record | Yes      |

#### ReportStorageUsageRecord

| Name         | Type     | Description                                      | Required |
| ------------ | -------- | ------------------------------------------------ | -------- |
| id           | string   |                                                  | Yes      |
| workspace_id | string   | The workspace ID                                 | Yes      |
| size_gb      | float    | The usage quantity(in GB) for the specified date | Yes      |
| end_time     | dateTime | The timestamp when this usage occurred           | Yes      |

#### ReportStorageUsageBody

| Name   | Type                                                  | Description             | Required |
| ------ | ----------------------------------------------------- | ----------------------- | -------- |
| record | [ReportStorageUsageRecord](#reportstorageusagerecord) | The usage report record | Yes      |

#### WorkspaceInfo

| Name         | Type   | Description            | Required |
| ------------ | ------ | ---------------------- | -------- |
| id           | string | Workspace ID           | Yes      |
| url          | string | Workspace URL          | Yes      |
| display_name | string | Workspace display name | Yes      |
