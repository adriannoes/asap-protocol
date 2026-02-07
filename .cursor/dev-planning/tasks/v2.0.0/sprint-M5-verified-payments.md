# Sprint M5: Verified Badge & Payments

> **Goal**: Stripe integration and Verified badge flow
> **Prerequisites**: Sprint M4 completed (Web App Features)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `apps/web/app/dashboard/verified/page.tsx` - Verified application page
- `apps/web/app/api/stripe/` - Stripe webhook handlers
- `apps/web/app/admin/reviews/page.tsx` - Admin review queue

---

## Context

This sprint enables monetization through the Verified badge at $49/month plus the admin review process.

---

## Task 5.1: Stripe Integration

### Sub-tasks

- [ ] 5.1.1 Create Stripe account/keys

- [ ] 5.1.2 Install Stripe SDK

- [ ] 5.1.3 Configure webhooks

- [ ] 5.1.4 Test mode setup

**Acceptance Criteria**:
- [ ] Stripe configured

---

## Task 5.2: Apply for Verified Flow

### Sub-tasks

- [ ] 5.2.1 /dashboard/verified page

- [ ] 5.2.2 Application form
  - Agent selection, business info

- [ ] 5.2.3 Submit application

- [ ] 5.2.4 Status tracking

**Acceptance Criteria**:
- [ ] Application flow working

---

## Task 5.3: Checkout Flow

### Sub-tasks

- [ ] 5.3.1 Stripe Checkout session

- [ ] 5.3.2 $49/month subscription

- [ ] 5.3.3 Success callback

- [ ] 5.3.4 Cancel callback

- [ ] 5.3.5 Subscription portal link

**Acceptance Criteria**:
- [ ] Payment flow working

---

## Task 5.4: ASAP CA Signing

### Sub-tasks

- [ ] 5.4.1 Generate ASAP CA keys (if not done)

- [ ] 5.4.2 On approval, sign manifest

- [ ] 5.4.3 Update Registry with Verified badge

- [ ] 5.4.4 Notify developer

**Acceptance Criteria**:
- [ ] Verified badge operational

---

## Task 5.5: Admin Review Queue

### Sub-tasks

- [ ] 5.5.1 /admin/reviews page (protected)

- [ ] 5.5.2 List pending applications

- [ ] 5.5.3 Approve/reject buttons

- [ ] 5.5.4 Trigger signing on approve

**Acceptance Criteria**:
- [ ] Admin can approve/reject

---

## Sprint M5 Definition of Done

- [ ] Stripe integration complete
- [ ] Payment flow working
- [ ] Verified badge operational
- [ ] Admin review queue functional

**Total Sub-tasks**: ~18
