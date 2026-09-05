# Backstop — Compliance Policy Specification (Rules R01..R14)

**Policy Engine Version:** `2026.09.01`  
**Lead Author & Maintainer:** [nika619](https://github.com/nika619)  
**Timezone Baseline:** Indian Standard Time (`UTC+05:30`)

---

## The 14 Machine-Executable Predicates

### R01 — Global Kill Switch
- **Rule Type:** Hard Stop
- **Citation:** Fintech Trust & Operational Safety Standard
- **Specification:** If `agent_enabled == False`, all automated recovery actions are immediately denied, returning `permitted = frozenset({NO_ACTION})`.

### R02 — Risk Hard Stop
- **Rule Type:** Anti-Money Laundering & Risk Isolation
- **Citation:** Prevention of Money Laundering Act (PMLA) 2002 & Razorpay Risk Policy
- **Specification:** Payments failing with `payment_risk_check_failed`, `compliance_violation`, or `payment_amount_tampered` route exclusively to `ESCALATE_HUMAN`. Zero automated customer recovery actions permitted.

### R03 — Terminal Cause Never Retry
- **Rule Type:** Waste Elimination & Network Protocol
- **Citation:** Card Network & NPCI Terminal Decline Operational Guidelines
- **Specification:** Root causes `INSTRUMENT_TERMINAL`, `RAIL_INELIGIBLE`, `RISK_DECLINE`, and `MERCHANT_CONFIG` can never be resolved by re-attempting the same payment rail. `RETRY_SAME_RAIL` is strictly denied.

### R04 — Maximum Attempt Cap (Max 3)
- **Rule Type:** Customer Goodwill & Issuer Rate Limiting
- **Citation:** Industry Best Practice
- **Specification:** If `attempt_no >= 3`, programmatic retries are denied to prevent payment fatigue and issuer blocking.

### R05 — Cool-off Windows Between Retries
- **Rule Type:** Exponential Time-Shifted Backoff
- **Citation:** Issuer Decline Protocol
- **Specification:** 
  - Attempt 0 → Attempt 1: 0h (immediate retry for transient network drops)
  - Attempt 1 → Attempt 2: 4h cool-off
  - Attempt 2 → Attempt 3: 48h cool-off

### R06 — TRAI Quiet Hours (09:00–21:00 IST)
- **Rule Type:** Anti-Harassment Communication Control
- **Citation:** Telecom Regulatory Authority of India (TRAI) Telecom Commercial Communications Customer Preference Regulations
- **Specification:** Outbound nudges (`NUDGE_CHECKOUT`, `SWITCH_RAIL_LINK`, `UPDATE_INSTRUMENT`) are strictly blocked outside 09:00–21:00 IST. The rule explicitly converts incoming timestamps to Indian Standard Time (`UTC+05:30`).

### R07 — Daily Contact Cap (Max 2 Contacts / Day)
- **Rule Type:** Anti-Harassment Communication Control
- **Citation:** Customer Protection Standard
- **Specification:** If `contacts_today(customer_ref) >= 2`, customer-facing messages are denied.

### R08 — DND / Opt-out Registry
- **Rule Type:** Statutory Consent Control
- **Citation:** TRAI National Do Not Call (NDNC) Registry & DPDP Act 2023
- **Specification:** If customer is marked DND or has revoked communication consent, customer-facing nudges are hard-blocked.

### R09 — RBI E-mandate Framework (2026): Pre-debit Notice ≥ 24h
- **Rule Type:** Statutory Regulatory Mandate
- **Citation:** Reserve Bank of India *Digital Payments — E-mandate Framework, 2026* (Notified 21 April 2026)
- **Specification:** For all recurring mandate debits (`is_recurring == True`), retry attempts require proof of a pre-transaction notification sent $\ge 24$ hours prior. If notice is absent or $< 24$ hours old, retry is strictly denied.

### R10 — RBI E-mandate Framework (2026): AFA Threshold Ceilings
- **Rule Type:** Statutory Regulatory Mandate
- **Citation:** Reserve Bank of India *Digital Payments — E-mandate Framework, 2026* (Notified 21 April 2026)
- **Specification:**
  - Standard recurring debits: Cap of **₹15,000** (1,500,000 paise) without Additional Factor of Authentication (AFA).
  - Specified categories (Insurance Premiums, Mutual Fund Subscriptions, Credit Card Bill Payments): Elevated ceiling of **₹1,00,000** (10,000,000 paise).
  - Amounts exceeding applicable ceiling cannot be auto-retried without customer AFA re-authorization.

### R11 — Active Promise-to-Pay Freeze
- **Rule Type:** Customer Grace & Collections Ethics
- **Citation:** Ethical Debt Recovery Standard
- **Specification:** If a customer commits to pay on a specific future date (`promise_to_pay_at > now`), all active chasing is frozen until the commitment window elapses.

### R12 — Merchant Configuration Bug Isolation
- **Rule Type:** Developer Bug Isolation
- **Citation:** Merchant Integrity Standard
- **Specification:** If failure is caused by merchant-side bugs (e.g. `input_validation_failed`, `order_amount_mismatch`), customer contact is strictly prohibited (`ALERT_MERCHANT` only).

### R13 — Promotional Incentive Budget Cap
- **Rule Type:** Treasury & Marketing Risk Limit
- **Citation:** Treasury Risk Policy
- **Specification:** Rail-switching promotional discounts are blocked when the merchant's batch incentive budget is exhausted.

### R14 — Control Arm Isolation (20% Held-Out)
- **Rule Type:** Scientific Causal Experimentation
- **Citation:** Experimentation Hygiene
- **Specification:** Cases deterministically assigned to the control group observe only (`frozenset({NO_ACTION})`), providing an empirical baseline for incremental lift measurement.
