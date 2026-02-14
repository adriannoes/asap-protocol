# Sprint M3: Verified Badge & Payments

> **Goal**: Stripe integration and Verified badge flow
> **Prerequisites**: Sprint M2 completed (Web App Features)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `apps/web/app/dashboard/verified/page.tsx` - Verified application page
- `apps/web/app/api/stripe/` - Stripe webhook handlers
- `apps/web/app/admin/reviews/page.tsx` - Admin review queue
- `apps/web/lib/email.ts` - Email service (Resend)

---

## Context

This sprint enables monetization through the Verified badge at $49/month plus the admin review process.

---

## Task 3.1: Stripe Integration

### Sub-tasks

- [ ] 3.1.1 Create Stripe account/keys
  - Dev/Test keys for local dev
  - Production keys for Vercel Env

- [ ] 3.1.2 Install Stripe SDK
  - `npm install stripe @stripe/stripe-js`

- [ ] 3.1.3 API Routes for Webhooks
  - **File**: `apps/web/app/api/stripe/webhook/route.ts`
  - **Events**:
    - `checkout.session.completed`: Provisional access
    - `invoice.payment_succeeded`: Renew access
    - `customer.subscription.deleted`: Revoke access
  - **Security**: `stripe.webhooks.constructEvent(body, sig, endpointSecret)`

- [ ] 3.1.4 Checkout Session API
  - **File**: `apps/web/app/api/stripe/checkout/route.ts`
  - **Logic**: `stripe.checkout.sessions.create(...)`
  - **Mode**: `subscription`
  - **Metadata**: `{ agent_id: string, github_user_id: string, type: 'verified_badge' }`
  - **Success URL**: `/dashboard/verified?success=true`

**Acceptance Criteria**:
- [ ] Stripe configured
- [ ] 3.1.5 Commit Stripe Setup
  - **Command**: `git commit -m "feat(payments): setup stripe webhooks and checkout"`

---

## Task 3.2: Apply for Verified Flow (Frontend)

### Sub-tasks

- [ ] 5.2.1 /dashboard/verified page

- [ ] 5.2.2 Application form
  - Agent selection, business info

- [ ] 5.2.3 Submit application

- [ ] 5.2.4 Status tracking

**Acceptance Criteria**:
- [ ] 5.2.5 Commit Verified UI
  - **Command**: `git commit -m "feat(web): add verified application form"`

---

## Task 3.3: Checkout Flow Integration

### Sub-tasks

- [ ] 5.3.1 Stripe Checkout session

- [ ] 5.3.2 $49/month subscription

- [ ] 5.3.3 Success callback

- [ ] 5.3.4 Cancel callback

- [ ] 5.3.5 Subscription portal link

**Acceptance Criteria**:
- [ ] 5.3.6 Commit Subscription
  - **Command**: `git commit -m "feat(payments): implement subscription flow"`

---

## Task 3.4: ASAP CA Signing Automation

### Context
When an agent is approved/paid, we need to sign its manifest with the ASAP CA Key.

> **Resolves**: [Issue #44](https://github.com/adriannoes/asap-protocol/issues/44) — Replace `sign_with_ca` simulation with real CA service integration.

### Sub-tasks

- [ ] 3.4.1 Generate ASAP CA Keypair
  - Store Private Key in GitHub Secrets (ASAP_CA_KEY)

- [ ] 3.4.2 GitHub Action for Signing
  - **File**: `.github/workflows/sign-agent.yml`
  - **Trigger**: `workflow_dispatch` (inputs: `agent_id`, `pr_number`)
  - **Steps**:
    1. Checkout code
    2. Install `asap-protocol` (pip)
    3. Retrieve Private Key from Secrets
    4. Run: `asap manifest sign --key env:ASAP_CA_KEY --in registry.json --target <agent_id>`
    5. Commit "Sign agent <agent_id>"
    6. Comment on PR: "Agent Verified & Signed successfully."

- [ ] 3.4.3 Integrate with Admin Dashboard
  - "Approve" button calls GitHub API `create-workflow-dispatch`

- [ ] 3.4.4 Notification (Email)
  - Send "Application Approved" email to developer (via Resend)
  - **Template**: "Congrats! Your agent X is now Verified."
  
**Acceptance Criteria**:
- [ ] GitHub Action signs manifest automatically
- [ ] 3.4.5 Commit Signing
  - **Command**: `git commit -m "feat(ci): add automatic manifest signing workflow"`
- [ ] Close [issue #44](https://github.com/adriannoes/asap-protocol/issues/44) with comment: "Resolved by Task 3.4 (ASAP CA Signing Automation). See sprint-M3-verified-payments.md."

---

## Task 3.5: Admin Review Queue

### Sub-tasks

- [ ] 5.5.1 /admin/reviews page (protected)

- [ ] 5.5.2 List pending applications

- [ ] 5.5.3 Approve/reject buttons

- [ ] 5.5.3 Approve/reject buttons
  - **Approve**: Determines agent_id -> Triggers CA Signing (3.4)
  - **Reject**: Triggers Stripe Refund (Partial/Full) -> Sends "Application Rejected" email

- [ ] 5.5.4 Stripe Refund Logic
  - API call to refund the payment intent
  - Cancel subscription immediately

**Acceptance Criteria**:
- [ ] 5.5.5 Commit Admin
  - **Command**: `git commit -m "feat(admin): implement review queue and refund logic"`

---

## Sprint M3 Definition of Done

- [ ] Stripe integration complete
- [ ] Payment flow working
- [ ] Verified badge operational
- [ ] Admin review queue functional

**Total Sub-tasks**: ~18

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
