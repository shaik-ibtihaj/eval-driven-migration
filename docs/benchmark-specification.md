# Stage 1 benchmark specification

## Scope

This document defines the evaluator-visible contract for migrating a legacy Flask order-management backend to FastAPI with PostgreSQL. It is a behavioral benchmark, not an implementation design. Stage 1 adds no application, database, harness, or evaluator code.

The evaluator compares normalized HTTP results and durable side effects. Generated IDs and timestamps may be normalized in later stages. Money values, authorization decisions, inventory quantities, transaction outcomes, payment-provider call counts, and audit-event counts must never be normalized away.

## Domain model

The benchmark has exactly these six domain entities:

| Entity | Required meaning and fields |
| --- | --- |
| `User` | `id`, unique normalized `email`, password credential, `role`, `active`, and timestamps. Passwords are never returned. |
| `Product` | `id`, `name`, `description`, `active`, `unit_price`, `currency`, `inventory_quantity`, and timestamps. `unit_price` is a fixed-precision decimal and inventory is a non-negative integer. |
| `Order` | `id`, `user_id`, `status`, fixed-precision `total_amount`, `currency`, and timestamps. It owns one or more order items. |
| `OrderItem` | `id`, `order_id`, `product_id`, positive integer `quantity`, and captured fixed-precision `unit_price`. Its captured price is immutable even if the product price later changes. |
| `Payment` | `id`, `order_id`, `status`, fixed-precision `amount`, `currency`, provider reference, idempotency key, and timestamps. Sensitive provider data is never returned. |
| `AuditEvent` | `id`, event type, actor user ID when known, subject type and ID, request/correlation ID, non-sensitive metadata, and timestamp. Events are append-only. |

Allowed enum values are closed sets:

- User roles: `customer`, `admin`
- Order states: `pending`, `paid`, `cancelled`
- Payment states: `pending`, `authorized`, `failed`

Other enum values are contract violations. `pending` may represent in-progress durable work, but no endpoint may expose a partially completed transaction as a successful result.

### Common HTTP rules

- JSON is used for every request body and response body. Money is represented as a base-10 string with exactly two fractional digits, for example `"19.90"`; JSON floating-point numbers are not accepted for money.
- Protected endpoints require `Authorization: Bearer <token>` for an active user. A missing, invalid, expired, or inactive-user token produces `401` and no business-state change. A `401` response includes `WWW-Authenticate: Bearer`.
- `Content-Type: application/json` is returned for all bodies. `X-Request-ID` is accepted or generated and returned, and is recorded on audit events.
- Errors have one normalized shape: `{"error":{"code":"machine_code","message":"safe message","details":{}}}`. `details` is an object and may be empty; it must not contain secrets, account-existence clues, provider internals, or another user's resource data.
- Malformed JSON is `400 malformed_json`; syntactically valid but invalid input is `422 validation_error`. Authentication is checked before resource ownership or existence is disclosed.
- A successful endpoint invocation emits exactly one durable `AuditEvent`. A replay of the same logical idempotent mutation returns its original normalized result and does not emit another event.

## Endpoint contracts

### `POST /auth/login`

**Authentication and authorization:** Public. Existing bearer credentials are ignored. The account must exist, be active, and match the supplied password, but every authentication failure is indistinguishable to the caller.

**Request:** `{"email":"user@example.com","password":"plaintext input"}`. Both fields are required non-empty strings; the email is normalized before comparison.

**Response:** `200` with `{"access_token":"opaque-or-jwt","token_type":"bearer","user":{"id":"...","email":"user@example.com","role":"customer"}}`. The response includes `Cache-Control: no-store`. Password material is absent.

**Status codes:** `200` success; `400` malformed JSON; `422` invalid field shape; `401` for a nonexistent account, wrong password, or inactive account. All `401` cases use the same `invalid_credentials` code and message.

**Error shape:** Every non-success response uses the common error envelope. Authentication failures always use `invalid_credentials` with identical safe wording and empty `details`.

**Database effects:** Success may update login metadata and appends exactly one `auth.login_succeeded` audit event. Failure does not change domain state; security telemetry outside these six entities is out of scope.

**External calls:** None.

### `GET /products`

**Authentication and authorization:** Requires any active authenticated `customer` or `admin`.

**Request:** No body. Optional `limit` and `offset` query parameters are non-negative integers; `limit` is from 1 through 100. Unknown query parameters are ignored.

**Response:** `200` with `{"items":[<product>],"limit":50,"offset":0}`. Products are ordered by `id`; only active products are listed. A product contains `id`, `name`, `description`, `active`, `unit_price`, `currency`, and `inventory_quantity`.

**Status codes:** `200` success; `401` authentication failure; `422` invalid pagination.

**Error shape:** Every non-success response uses the common error envelope. Pagination errors use `validation_error` with field-level entries in `details`.

**Database effects:** No product or inventory mutation. Success appends exactly one `product.listed` audit event.

**External calls:** None.

### `GET /products/{product_id}`

**Authentication and authorization:** Requires any active authenticated `customer` or `admin`.

**Request:** No body. `product_id` must be a valid identifier in the implementation's chosen ID format.

**Response:** `200` with one product object in the same representation used by the product list. Both active and inactive products are readable so clients can distinguish an unavailable product from an unknown one.

**Status codes:** `200` success; `401` authentication failure; `404 product_not_found` for an unknown well-formed ID; `422` for an invalid ID shape.

**Error shape:** Every non-success response uses the common error envelope. A malformed ID uses `validation_error`; an unknown ID uses `product_not_found` without database details.

**Database effects:** No product or inventory mutation. Success appends exactly one `product.viewed` audit event.

**External calls:** None.

### `POST /orders`

**Authentication and authorization:** Requires an active authenticated `customer` or `admin`. The new order always belongs to the authenticated user; a client-supplied user ID is rejected. An admin receives no ability through this endpoint to order for another user.

**Request:** Requires `Idempotency-Key` with a non-empty value of at most 255 characters and a JSON body `{"items":[{"product_id":"...","quantity":2}]}`. The list must contain at least one item, quantities must be positive integers, and duplicate product IDs are rejected. The key is scoped to the authenticated user and this operation. Reuse with a different normalized request is `409 idempotency_conflict`.

**Response:** `201` with `Location: /orders/{order_id}` and `{"id":"...","user_id":"...","status":"paid","items":[{"product_id":"...","quantity":2,"unit_price":"19.90"}],"total_amount":"39.80","currency":"USD","payment":{"id":"...","status":"authorized"}}`. Items are ordered by product ID. Product prices are captured at creation and totals use fixed-precision decimal arithmetic. Replaying the same key and request returns the same normalized body and status without duplicating effects.

**Status codes:** `201` success or identical replay; `400` malformed JSON or missing/invalid idempotency header; `401` authentication failure; `404 product_not_found`; `409 idempotency_conflict` or `insufficient_inventory`; `422` invalid item shape, duplicate product, inactive product (`product_inactive`), mixed currencies, or other semantic validation; `402 payment_failed`; `503 payment_unavailable` for an indeterminate/unavailable provider. A `503` may include `Retry-After`.

**Error shape:** Every non-success response uses the common error envelope and the machine code listed above. Product and provider implementation details are excluded from `details`.

**Database effects:** On `201`, one `Order`, its `OrderItem` rows, and one `Payment` are durably created; the order is `paid`, the payment is `authorized`, every stock quantity is reduced once, and exactly one `order.created` audit event is appended. These effects are one all-or-nothing outcome. Any non-`201` result creates none of those domain rows, consumes no inventory, and emits no success audit event. Idempotency bookkeeping is an implementation detail and is not a seventh domain entity.

**External calls:** The payment provider receives at most one authorization call for a logical idempotency key, with the exact fixed-precision total, currency, and a provider idempotency key. Validation, product activity, and available inventory are checked before that call. `payment_failed` means one declined/failed authorization; `payment_unavailable` means no second call may be made unless the same key can be resolved safely. Any authorization followed by local failure must be compensated so the externally observable outcome is not a charge without the successful order.

### `POST /orders/{order_id}/cancel`

**Authentication and authorization:** Requires an active authenticated user. Only the order owner may act; the rule also applies to `admin`. A nonexistent order and another user's order both return the same `404 order_not_found`, preventing existence disclosure.

**Request:** Requires `Idempotency-Key` under the same syntax and conflict rules as order creation. No JSON body is required; a non-empty body is `422 validation_error`.

**Response:** `200` with `{"id":"...","status":"cancelled"}`. If the order is already cancelled, the same normalized success is returned. Repeated cancellation, including a new idempotency key, is idempotent.

**Status codes:** `200` first cancellation or replay; `400` missing/invalid idempotency header; `401` authentication failure; `404 order_not_found` for unknown or foreign orders; `409 idempotency_conflict`; `422` invalid order ID or non-empty body; `503 payment_unavailable` when a required provider operation cannot complete.

**Error shape:** Every non-success response uses the common error envelope. Unknown and foreign orders use identical `order_not_found` bodies; provider internals are excluded from `payment_unavailable` details.

**Database effects:** On the first cancellation, the order becomes `cancelled`, each quantity previously consumed by that order is restored exactly once, and exactly one `order.cancelled` audit event is appended in the same transaction. A pending order that never consumed inventory restores zero. Repetition changes no rows, restores no additional inventory, and emits no additional audit event.

**External calls:** If the payment is `authorized`, the provider receives at most one void/refund call for the cancellation's logical operation, using provider idempotency. No payment call is made for a failed or never-authorized payment. A provider failure must not expose a locally successful cancellation; it returns `503 payment_unavailable` with no committed cancellation, restoration, or success audit event.

## Required invariants

These twelve invariants are mandatory under normal requests, retries, concurrent requests, provider failures, and database failures:

1. Inventory never becomes negative.
2. Successful order creation and stock reduction are atomic: both commit or neither commits.
3. An `OrderItem`'s captured purchase price never changes.
4. A failed payment does not consume inventory.
5. Users cannot read, mutate, or infer another user's orders through the specified endpoints.
6. Cancellation restores all inventory consumed by the order exactly once.
7. Repeated cancellation is idempotent and produces the same normalized successful result.
8. Inactive products cannot be ordered.
9. All money calculations and storage use fixed-precision decimal arithmetic; binary floating point is forbidden.
10. Authentication failures do not expose whether an account exists or is active.
11. An idempotency key cannot create an order twice or cause more than one charge/authorization for the logical operation.
12. Each successful logical operation emits its specified audit event exactly once; failures and idempotent replays emit no success event.

## Evaluator-observable behavior

For each test case, the evaluator may observe and compare:

- HTTP status and normalized JSON body, including stable error codes and safe messages.
- Important request/response headers: `Authorization`, `Idempotency-Key`, `Content-Type`, `Location`, `WWW-Authenticate`, `Cache-Control`, `Retry-After`, and `X-Request-ID` when applicable.
- Committed database changes across all six entities, including the absence of partial writes.
- Payment-provider operation, amount, currency, idempotency key, result, ordering, and call count.
- Audit-event type, actor, subject, correlation, non-sensitive metadata, and exact event count.
- Any invariant violation, including violations visible only under retries, concurrency, or injected failures.

Later normalization may replace generated IDs with stable placeholders and timestamps with deterministic values or ordering tokens. It must preserve referential relationships. It may not alter or ignore money, authorization decisions, inventory quantities, transaction commit/rollback outcomes, provider calls, payment outcomes, or audit-event counts.
