# EduConnect Backend — Hardening, RBAC Redesign, Events & Monetization

This document covers every change made in this pass. Changes are grouped by
category; each entry names the file(s) touched and why. All claims of
"fixed" or "verified" below were confirmed with an actual running FastAPI
app + SQLite database in this session (see "How this was verified" at the
bottom) — not just read through.

---

## 1. Critical bug: SUPER_ADMIN was powerless

**The bug:** every admin-gating check in the codebase compared a user's role
directly against `UserRole.ADMIN` (`role != UserRole.ADMIN`, or membership
in a set that included `ADMIN` but not `SUPER_ADMIN`). Since `SUPER_ADMIN`
never equals `ADMIN`, this meant the super admin role — the one meant to
have the *most* access — was locked out of nearly every admin-gated
endpoint and permission check in the platform: the admin dashboard,
category/hub management, content moderation, content authoring, education
resource creation, children's-section content, and partnership activation.
A super admin account had *less* effective access than a plain admin.

**Fixed in 6 places**, all using the same pattern (`is_admin_tier(role)`
from the new `app/core/permissions.py` instead of a raw equality check):

- `app/core/deps.py` — `require_admin`, `require_moderator_or_admin`,
  `require_writer_teacher_or_admin`
- `app/services/content_service.py` — `ensure_can_write_content`,
  `ensure_content_owner_or_admin`, and the published-content edit guard in
  `update_content`
- `app/services/education_service.py` — `ensure_can_create_education_resource`
  and the ownership check in `create_education_resource`
- `app/services/children_service.py` — `ensure_can_create_children_content`
- `app/services/writer_service.py` / `app/services/feed_service.py` — the
  `WRITER_ROLES` set and writer-search role filter now include
  `SUPER_ADMIN` too, for consistency (lower severity — not an access-control
  bug, but a super admin who writes content should show up in writer search)

---

## 2. Granular permission system ("factor admins down to specific functions")

New files:
- `app/core/permissions.py` — the `Permission` enum (16 granular
  capabilities: `USERS_VIEW`, `USERS_MANAGE`, `CONTENT_MODERATE`,
  `CONTENT_MANAGE`, `CATALOG_MANAGE`, `ROLE_REQUESTS_REVIEW`,
  `PARTNERSHIPS_MANAGE`, `PAYOUTS_MANAGE`, `EVENTS_MANAGE`,
  `EVENTS_MODERATE`, `STUDENTS_VERIFY`, `BADGES_MANAGE`, `REPORTS_MANAGE`,
  `SYSTEM_SETTINGS`), the `STAFF_ROLES` set, and the `ROLE_RANK` hierarchy.
- `app/models/permission.py` — `AdminPermission`, a simple (user_id,
  permission) grant table.

How it works: **SUPER_ADMIN implicitly holds every permission** and passes
every check automatically. A plain **ADMIN holds none by default** — a
super admin grants exactly the permissions a given admin needs via
`POST /admin/users/{id}/permissions`. `app/core/deps.py::require_permission(...)`
is the dependency used at each endpoint to enforce this.

**Staff-role escalation is blocked structurally, not just by convention:**
in `app/services/admin_service.py::update_user_role`, a plain admin (even
one holding `USERS_MANAGE`) can only move a user between ordinary member
roles (READER, WRITER, TEACHER, STUDENT, PARENT). Assigning or removing a
staff role (MODERATOR, ADMIN, SUPER_ADMIN) — or changing the role of an
existing staff member at all — requires `SUPER_ADMIN`. This closes what
was previously a direct privilege-escalation path: **any existing ADMIN
could set any user's role to ADMIN or SUPER_ADMIN**, including a second
account they controlled. Verified in testing (see below).

**Safety net:** the last remaining `SUPER_ADMIN` account cannot be demoted
or deactivated by anyone, including another super admin — this prevents
accidentally locking the platform out of its top administrative tier.

Endpoints rewired from blanket `require_admin` to granular permissions:
`app/routers/admin.py`, `app/routers/categories.py`, `app/routers/hubs.py`,
`app/routers/partnerships.py`, `app/routers/role_requests.py`.

---

## 3. Critical security fix: M-Pesa callback could be forged for free partnerships

**The vulnerability:** `POST /partnerships/mpesa/callback` was a fully
open, unauthenticated endpoint. Safaricom's Daraja API does not sign STK
push callbacks in any way. The only thing the original handler trusted was
`CheckoutRequestID` — a value returned **directly to the paying client**
in the `/partnerships/start` response. Concretely: any user could start
checkout, never actually pay, then POST a forged "ResultCode: 0" success
payload straight to the callback endpoint using their own leaked
`CheckoutRequestID`, and receive a fully active paid partnership for free.

**Fixed** in `app/routers/partnerships.py` + `app/core/config.py`:
- The callback route is now `POST /partnerships/mpesa/callback/{secret}`,
  where `{secret}` is a long random value (`MPESA_CALLBACK_SECRET`) known
  only to the server and configured as part of the callback URL registered
  with Safaricom — never returned to any client.
- A wrong or missing secret gets an identical 404 (not 401/403), so a
  prober can't distinguish "wrong secret" from "route doesn't exist."
- **Startup fails fast** (`app/main.py`) if `PAYMENT_MODE=mpesa` is set
  without `MPESA_CALLBACK_SECRET` configured, rather than silently running
  with an exposed webhook.
- Rate limiting added (30 req/min) via the new `app/core/rate_limit.py`.
- The handler now always returns HTTP 200 to Safaricom once the secret
  check passes (even if internal processing fails), since Daraja
  aggressively retries non-200 responses — errors are logged instead.

**Also fixed:** the callback previously trusted `ResultCode: 0` alone.
`app/services/partnership_service.py::handle_mpesa_callback` now
cross-checks the `Amount` field in the callback metadata against the
expected payment amount before activating — an amount mismatch marks the
payment `FAILED` and the partnership `CANCELLED` instead of granting
access. Verified with an automated test simulating an underpaid callback.

---

## 4. Monetization leak: student/teacher discount pricing had no eligibility check

**The bug:** `PartnershipPlan.STUDENT_PARTNER` (KES 150) and
`TEACHER_PARTNER` (KES 200) — discounted relative to the KES 300/3000
monthly/annual plans — had **zero server-side check** that the purchasing
user was actually a student or teacher. Any reader could pass
`plan=STUDENT_PARTNER` and pay the discounted rate.

**Fixed** in `app/services/partnership_service.py::ensure_plan_eligibility`,
called from `start_partnership_checkout`: `STUDENT_PARTNER` requires
`role == STUDENT`, `TEACHER_PARTNER` requires `role == TEACHER` (admin-tier
accounts are exempt so support staff can test the flow). Verified with an
automated test confirming a plain reader gets a 403.

---

## 5. New monetization feature: referral commission ledger

`Partnership.referral_creator_id` already existed in the original schema
but **nothing ever read or wrote to it beyond storing the value** — no
reward mechanism existed. This turns it into an actual creator incentive.

New files:
- `app/models/monetization.py` — `ReferralEarning` (PENDING/PAID/VOID),
  storing a snapshot of the source amount and commission rate at credit
  time (so a future rate change doesn't silently recompute history).
- `app/services/monetization_service.py` — `credit_referral_commission`
  (10% of the payment amount, called automatically from
  `activate_partnership_from_payment` after a successful M-Pesa payment),
  plus summary/listing functions for creators and admin payout management.
- `app/schemas/monetization.py`

New endpoints:
- `GET /partnerships/referrals/summary`, `GET /partnerships/referrals/earnings`
  (creator-facing, in `app/routers/partnerships.py`)
- `GET /admin/payouts/pending`, `POST /admin/payouts/{id}/mark-paid`
  (admin-facing, gated by the new `PAYOUTS_MANAGE` permission, in
  `app/routers/admin.py`)

Verified end-to-end: crediting fires on payment success, is idempotent
against duplicate Safaricom callback delivery, and computes the correct
10% commission.

---

## 6. New feature: marketing events (competitions, workshops, book clubs)

New files:
- `app/models/event.py` — `Event` (one table, `type` discriminator across
  COMPETITION/WORKSHOP/BOOK_CLUB rather than three separate tables — they
  share the same lifecycle, participation model, and discovery surface),
  `EventParticipant` (RSVP → ATTENDED → SUBMITTED/COMPLETED → WITHDREW).
- `app/services/event_service.py` — full CRUD + participation lifecycle,
  student-only gating, partnership-required gating (a host can mark a
  workshop as requiring an active partnership to join — a direct
  monetization lever reusing the existing partnership-gating pattern from
  content), slug generation with collision handling.
- `app/schemas/event.py`, `app/routers/events.py`

Who can host: WRITER, TEACHER, or admin-tier accounts
(`ensure_can_host_events`) — this is the direct "build creator-student
relationships" mechanism from your stated priorities: a teacher can run a
CBC-aligned book club, a writer can run a competition, and both build a
direct relationship with the students who join.

Curriculum targeting: `Event.curriculum_tags` (e.g. `["CBC", "Grade 8"]`)
and `Event.student_only` (gated by the same student-eligibility check used
for the partnership discount — role STUDENT or a verified StudentProfile).

Verified end-to-end with an automated test: create → publish → student-only
RSVP gating → attend → XP awarded → leaderboard reflects it → non-host
cannot mark attendance on someone else's event → non-student blocked from
a student-only event.

**On "flag some things down or up":** the codebase already has a
featured-content toggle (`POST /admin/content/{id}/feature`, gated by the
new `CONTENT_MANAGE` permission) that flags content up/down in visibility.
I didn't build a separate upvote/downvote system since this seemed to be
the same concept already covered — flag if you meant something else (e.g.
a reader-facing upvote/downvote on content or comments).

---

## 7. New feature: student identity & verification

New files:
- `app/models/student.py` — `School`, `StudentProfile` (a one-to-one
  extension of `User`, not a separate account type — most users won't be
  students, and a missing profile row just means "not verified,"
  independent of whether `role == STUDENT`).
- `app/services/student_service.py` — school search/creation, affiliation
  update, email-code verification flow (code generation + confirmation;
  actual email delivery is stubbed with a logged code — see TODO below),
  and an admin manual-verification path.
- `app/schemas/student.py`, `app/routers/students.py`

This is the foundation both the student-only event gating and the
STUDENT_PARTNER discount's strongest eligibility check build on.

**TODO before production:** `request_verification` in
`student_service.py` logs the verification code instead of emailing it —
wire in your actual email provider at the marked call site.

---

## 8. New feature: XP ledger, leaderboard, badges

New files:
- `app/models/gamification.py` — `XPLedgerEntry` (append-only — never
  updated or deleted, so there's a full audit trail and any time-window
  leaderboard can be computed by filtering `earned_at` rather than
  maintaining separate running counters that can drift), `Badge`,
  `UserBadge`.
- `app/services/gamification_service.py` — `award_xp` (centralised XP
  rules: RSVP +5, attend +20, submit +50, complete +30), leaderboard
  queries (all-time / rolling 30-day, optionally school-scoped via a join
  through `StudentProfile`), and a small explicit badge-condition checker
  (`events_attended`, `total_xp` thresholds) run after every XP grant.
- `app/schemas/gamification.py`, `app/routers/leaderboard.py`

Badge creation is admin-gated by the new `BADGES_MANAGE` permission
(`POST /admin/badges`).

---

## 9. Other hardening

- **File uploads** (`app/core/storage.py`): previously accepted any file
  extension with no size limit — a public `/uploads/` static mount serving
  arbitrary uploaded files with no validation. Now enforces an extension
  allowlist per asset type (images vs. documents) and streams-and-aborts
  on exceeding a size cap (10MB images / 50MB files) rather than buffering
  an unbounded upload into memory first.
- **Password policy** (`app/schemas/auth.py`): `RegisterRequest.password`
  had no length constraint at all (a separate schema, `UserCreate`, did —
  but the actual public registration endpoint used the unconstrained one).
  Now requires 8–128 characters, matching `UserCreate`.
- **Rate limiting** (`app/core/rate_limit.py`, new): a lightweight
  in-process sliding-window limiter applied to `/auth/login` (10/min),
  `/auth/register` (5/min), and the M-Pesa callback (30/min). Documented
  in the module docstring as a single-instance solution — swap for
  Redis-backed limiting if you scale to multiple backend replicas.
- **CORS** (`app/main.py`): tightened from wildcard methods/headers to an
  explicit list, since `allow_credentials=True` combined with wildcards is
  broader than necessary (the origin list was already explicit, which is
  the part that matters most).

---

## 10. Bugs found and fixed that were unrelated to the stated ask, but broke real functionality

- **`TokenResponse` was missing its `user` field** (`app/schemas/auth.py`).
  `routers/auth.py` had always constructed
  `TokenResponse(access_token=token, user=user)`, but the schema never
  declared a `user` field — Pydantic v2's default `extra="ignore"` silently
  dropped it rather than erroring. Every login and registration response
  was missing the user object the frontend almost certainly expects
  alongside the token. Fixed by adding the field.
- **`admin_activate_partnership` was referenced but never implemented.**
  `routers/partnerships.py` imported and called this function (for an
  admin manually activating a partnership, e.g. for an off-platform
  payment), but it didn't exist anywhere in `partnership_service.py` —
  calling that endpoint would have raised an `ImportError` at request
  time. Implemented it (extends from current expiry if still active,
  otherwise from now, so a re-activation doesn't lose remaining paid time).
- **Dead duplicate code removed** from the original `partnership_service.py`
  (a second, commented-out copy of `start_partnership_checkout`).

---

## How this was verified

Every claim above of "fixed" or "verified" was checked with a real running
instance in this session, not just read through:

1. Every `.py` file byte-compiled cleanly (`python -m py_compile`).
2. The full FastAPI app imports cleanly and registers all 123 routes
   (`from app.main import app`) against a SQLite database with required
   env vars set.
3. `Base.metadata.create_all()` successfully creates all 29 tables
   (20 original + 9 new) with no errors.
4. An end-to-end `TestClient` session exercised, and confirmed passing:
   - Registration returns the user object (bugfix confirmed)
   - A plain reader is blocked from the admin dashboard and from hosting
     events
   - A `SUPER_ADMIN` account **can** access the admin dashboard and **can**
     host events (the core bug fix)
   - A plain `ADMIN` with no granted permissions is blocked from listing
     users; after a `SUPER_ADMIN` grants `USERS_VIEW`, the same admin can
     list users but still cannot change roles without `USERS_MANAGE`
   - A plain `ADMIN` holding `USERS_MANAGE` **cannot** promote anyone to
     `SUPER_ADMIN` (privilege escalation blocked) but **can** promote to an
     ordinary role like `WRITER`
   - The M-Pesa callback rejects a wrong secret with 404 and accepts the
     correct one
   - A plain reader is blocked from purchasing the `STUDENT_PARTNER`
     discount plan
   - A weak password is rejected at registration (422)
5. A second `TestClient` session walked the full event lifecycle: create →
   reject-RSVP-while-draft → publish → student-only RSVP gating → XP
   awarded and reflected on `/leaderboard/me` → host marks attended → XP
   accumulates correctly → global leaderboard reflects it → a non-host is
   blocked from marking attendance → a non-student is blocked from a
   student-only event.
6. A direct service-layer test drove the M-Pesa callback through a
   simulated legitimate Safaricom success payload: payment marked
   SUCCESS, partnership activated with the correct expiry, referral
   commission credited at exactly 10%, duplicate callback delivery does
   NOT double-credit (idempotency), and an amount-mismatch callback
   correctly marks the payment FAILED and partnership CANCELLED instead of
   granting access.
7. The previously-broken `admin_activate_partnership` endpoint was
   exercised via HTTP end-to-end and confirmed working.
8. The new Alembic migration was verified in isolation: chains cleanly
   onto the existing single head (`568c6b5dc7ca`), applies cleanly against
   a database stamped to that prior state (creating all 9 new tables with
   correct foreign keys and indexes), and the downgrade path runs cleanly
   as well.

## What wasn't done / next steps worth considering

- Real email delivery for student verification codes (currently logged,
  not sent) — see `student_service.py::request_verification`.
- The in-process rate limiter is single-instance only; move to Redis if
  you scale horizontally.
- File upload validation checks extension + declared content-type, not
  magic-byte content sniffing — add `python-magic` if you want a stronger
  guarantee against a mislabeled file extension.
- No automated test suite was added to the repo itself (the verification
  above was run ad hoc in this session) — worth adding `pytest` +
  `httpx.AsyncClient`-based tests covering the scenarios verified above so
  they're guarded against regression going forward.
