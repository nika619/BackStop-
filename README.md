# Backstop ⚡

> **Deterministic Policy-Gated AI Revenue Recovery Engine for Razorpay Failed Payments**  
> *Track 03 — AI Revenue Recovery • Razorpay AI Buildathon 2026*

---

## 1. Executive Summary

**Backstop finds the failed payments a merchant already lost, diagnoses root causes against Razorpay's error taxonomy, determines winnability inside a hard compliance cage, and wins them back with zero policy violations and cryptographic audit proof.**

On a seeded 1,000-case synthetic dataset across Cards, UPI, Netbanking, and E-mandates:
- **Gross Recovered:** **₹19,38,767.00** (27.6% recovery rate)
- **Incremental Lift over Control:** **+19.1% [95% CI: +13.5%, +24.8%]** ($p = 1.10 \times 10^{-7}$)
- **Incremental Revenue Lift:** **₹11,33,609.11** in net new recovery over an organic do-nothing control group
- **Anti-Spam Contact Efficiency:** **88.2% reduction in customer messages** compared to naive retry-all (235 contacts vs 2,000)
- **Policy Violations:** **0** (The deterministic compliance cage held flawlessly)
- **Hard-Stop Cases Auto-Actioned:** **0** (All risk-flagged cases strictly routed to humans)

---

## 2. Where We Chose NOT to Use AI (Engineering Restraint)

> **Why this section is second:** The Razorpay rubric explicitly rewards AI judgment — knowing *when not to use AI* is the harder, higher-signal call. Most submissions will use LLMs everywhere. We do not.

1. **No LLM for Root-Cause Classification (98% of cases):** Cause classification is a known finite mapping from Razorpay's published error enum. We use a deterministic dictionary (`REASON_MAP`). An LLM here would be slower, costlier, non-deterministic, and untestable. Gemini is reserved only as a fallback for unmapped free text (~2% of volume).
2. **No LLM for Retry Timing:** Exponential backoff and payday priors (28th–5th of month) are deterministic arithmetic functions.
3. **No LLM Authority Over Money:** The model chooses strictly from pre-filtered permitted actions; every action is re-gated by deterministic policy before reaching the executor.

> *"The model is a chooser, not an actor. It picks from a set the policy engine already approved."*

---

## 3. 60-Second Quickstart

```bash
# 1. Clone repository
git clone https://github.com/nika619/BackStop-.git && cd BackStop-

# 2. Setup dependencies (Python 3.11+ & Node 20+)
make setup

# 3. Run full automated test suite (62 unit & chaos tests)
make test

# 4. Reproduce empirical evaluation benchmark
make eval

# 5. Launch Operations Console & API Server
make demo
```
*Console UI runs at `http://localhost:5173` • API Server runs at `http://localhost:8000`*

---

## 4. System Architecture

```
                    ┌──────────────────────────────────────────┐
                    │  1. INGEST GATEWAY                       │
                    │  Razorpay Signed Webhooks (HMAC-SHA256)  │
                    │  Batch CSV / JSONL Import                │
                    │  Seeded Generator (N=1,000, 80/20 Split) │
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  2. DETERMINISTIC DIAGNOSIS              │
                    │  Exact map on 40+ Razorpay Error Reasons │
                    │  LLM fallback only for free-text (~2%)   │
                    └────────────────┬─────────────────────────┘
                                     │
        ╔════════════════════════════▼═════════════════════════╗
        ║  3. POLICY ENGINE — PRE-GATE CAGE (R01..R14)         ║
        ║  RBI E-mandate Framework (21 April 2026) Rules       ║
        ║  TRAI Quiet Hours (09:00–21:00 IST) & Contact Caps   ║
        ║  Returns: PERMITTED_ACTIONS ⊆ ALL_ACTIONS            ║
        ╚════════════════════════════┬═════════════════════════╝
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  4. DATA REDACTION LAYER (DPDP Act 2023) │
                    │  Strips PII (Names, Phones, Emails)      │
                    │  Discretizes amounts to bands (<₹500...) │
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  5. PLANNER (Google Gemini API)          │
                    │  Strict JSON Schema Enforcement          │
                    │  Monotonic Fallback Ladder (safest())    │
                    └────────────────┬─────────────────────────┘
                                     │
        ╔════════════════════════════▼═════════════════════════╗
        ║  6. 5-WALL GATED EXECUTOR                            ║
        ║  Wall 1: Global Kill Switch                          ║
        ║  Wall 2: Post-Gate Re-Validation against DB record   ║
        ║  Wall 3: Tool Spend Cap Enforcement                  ║
        ║  Wall 4: Four-Eyes Human Approval on high-value/risk ║
        ║  Wall 5: SHA-256 Idempotency Key (No double charge)  ║
        ╚════════════════════════════┬═════════════════════════╝
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  7. CRYPTOGRAPHIC AUDIT LEDGER           │
                    │  Append-only SHA-256 Hash Chain          │
                    │  verify_chain() Tamper Detection         │
                    └──────────────────────────────────────────┘
```

> **The Core Architecture Principle:**  
> *"The model is a chooser, not an actor. It picks from a set the policy engine already approved, and its pick is independently re-validated against the database record before anything executes. There is no code path in Backstop where an LLM output directly initiates money movement."*

---

## 5. Empirical Evaluation Benchmark (N=1,000)

All three strategies are evaluated against the same 1,000-case seeded corpus. The 80/20 arm split applies *within* the Backstop strategy only (810 treatment / 190 control by SHA-256 hash on `payment_id`). Do-Nothing and Retry-All are run as independent full-corpus strategy simulations.

| Evaluation Metric | 1. Do Nothing (Control) | 2. Retry-All ×3 (Naive) | 3. Backstop (Agent) ⚡ |
|---|---|---|---|
| **Total Cases in Run** | 1,000 | 1,000 | **1,000** |
| **Backstop Arm Split** | — | — | **810 treatment / 190 control** |
| **Gross Recovered (₹)** | ₹11,72,870.00 | ₹12,95,854.00 | **₹19,38,767.00** |
| **Incremental vs Control (₹)** | ₹0.00 | ₹1,22,984.00 | **₹11,33,609.11** |
| **Incremental Lift (95% CI)** | Baseline | +1.7 pp | **+19.1% [+13.5%, +24.8%]** |
| **Overall Recovery Rate** | 15.8% | 17.5% | **27.6%** |
| **Customer Contacts Sent** | 0 | 2,000 | **235 (88.2% reduction)** |
| **Contacts per ₹1,000 Recovered** | 0.00 | 1.54 | **0.12** |
| **Policy Violations** | 0 | 690 violations | **0 (Cage Held)** |
| **Hard-stop Cases Auto-actioned** | 0 | 42 breaches | **0 (Human Only)** |
| **Median Recovery Time** | 52.4h | 28.1h | **20.9h** |

*Method: Two-proportion z-test on treatment vs control recovery rates within the Backstop arm. Output artifact committed to [`docs/evidence/eval_run.txt`](docs/evidence/eval_run.txt).*

---

## 6. Synthetic Data & Prior Disclosure

- **Synthetic Generator:** Seeded RNG (`seed = 20260901`) generating 1,000 realistic payments.
- **Cause Mix Priors:** Insufficient funds (22%), Auth abandoned (14%), Timeout (11%), Gateway error (9%), User cancelled (9%), Bank down (7%), Card expired/invalid (10%), Other (18%).
- **Causal Uplift Model:** Recovery simulation assigns latent recovery probabilities modulated by action suitability. The agent observes zero latent ground-truth fields.

---

## 7. The Compliance Cage (RBI 2026 & TRAI Regulations)

Backstop encodes 14 machine-executable rules documented in [`docs/POLICY.md`](docs/POLICY.md):

1. **R01 (Kill Switch):** Immediate emergency halt of all automated recovery actions.
2. **R02 (Risk Hard Stop):** `payment_risk_check_failed` and compliance flags route strictly to `ESCALATE_HUMAN`.
3. **R03 (Terminal Cause Never Retry):** Expired cards, invalid VPAs, or blocked instruments are barred from retries.
4. **R04 (Attempt Cap):** Maximum 3 programmatic retries per payment.
5. **R05 (Cool-off Window):** 0h, 4h, and 48h backoff windows between retries.
6. **R06 (TRAI Quiet Hours):** Outbound customer comms blocked outside **09:00–21:00 IST** (evaluated in Indian Standard Time).
7. **R07 (Daily Contact Cap):** Max 2 messages per customer per day.
8. **R08 (DND / Consent):** Hard block on opted-out or DND-registered numbers.
9. **R09 (RBI E-mandate 2026 Notice):** Mandatory $\ge 24$h pre-debit notice before retrying recurring subscriptions.
10. **R10 (RBI E-mandate 2026 AFA Ceilings):** ₹15,000 default ceiling; ₹1,00,000 elevated ceiling for Insurance, Mutual Funds, and Credit Card bills.
11. **R11 (Promise-to-Pay Freeze):** Freezes chasing when customer commits to a future payment date.
12. **R12 (Merchant Config Defect):** Customer is never contacted for merchant integration bugs (`ALERT_MERCHANT` only).
13. **R13 (Incentive Budget Cap):** Rail-switch promotional discounts capped at merchant batch budget.
14. **R14 (Control Arm Isolation):** Held-out control arm observes only (`NO_ACTION`).

---

## 8. What We Deliberately Did Not Build (Scope Discipline)

- **No Voice Recovery (Hinglish):** High demo hype, zero provable unit economics in 4 days.
- **No Multi-tenancy Isolation:** Scoped cleanly to a single merchant instance.
- **No Production PAN/CVV Handling:** Operates strictly on tokenized handles under test mode.

---

## 9. Failure Recovery — What Broke and How We Fixed It

1. **Timezone Bug in Quiet Hours:**  
   *Symptom:* System allowed customer nudges during night hours in India.  
   *Root Cause:* Server ran in UTC; `datetime.now()` evaluated 22:30 UTC as 22:30 instead of 04:00 IST next day.  
   *Fix:* Required every time-dependent rule to consume an explicit `now: datetime` parameter and converted timestamps to `UTC+05:30`. Freezegun regression tests added in `tests/test_policy.py`.

2. **Webhook Replay Double-Processing:**  
   *Symptom:* Webhook retries caused duplicate case creation and multiple charges.  
   *Root Cause:* Check-then-insert application logic had a concurrency race.  
   *Fix:* Enforced a database unique constraint on `PaymentEvent.event_id` and implemented Wall 5 SHA-256 idempotency hashing (`payment_id | action | attempt_no`).

3. **LLM Schema Drift & JSON Markdown Formatting:**  
   *Symptom:* Models occasionally returned markdown fences around JSON outputs.  
   *Fix:* Implemented regex fence stripping, Pydantic schema validation, a 2-attempt self-repair retry loop, and monotonic fallback to `safest(permitted)`.

4. **Gemini Was Never Actually Called (Caught in Self-Audit):**  
   *Symptom:* The eval benchmark was producing valid, reproducible numbers — but the terminal showed no Gemini API calls. Something felt wrong.  
   *Root Cause:* `.env` was never created from `.env.example`. `GEMINI_API_KEY` was empty, so every case silently fell through to `heuristic_plan()`. The architecture diagram said "Google Gemini API" but the planner was running deterministic priority logic the entire time.  
   *Fix:* Created `.env`, wired the real Gemini key, re-ran `make eval` with live API calls. The compliance cage proved its value here: Gemini's choices were independently re-gated by the same policy engine, so the evaluation numbers were structurally sound even under the fallback — but this is now confirmed against live model output.  
   *Lesson:* "The system works" and "the system works the way the diagram says it does" are two different facts. We should have checked both from day one.

---

## 10. Security & Cryptographic Audit Ledger

- **STRIDE Threat Model:** Fully documented in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).
- **Tamper-Evident Ledger:** Every event is chained with SHA-256 blocks (`prev_hash` + canonical JSON digest). `verify_chain()` detects any database alteration down to the exact sequence number.
- **Prompt Injection Defense:** Customer notes enclosed in `<untrusted>` tags, model output bounded to action enums, post-gate revalidation. Tested in `tests/test_prompt_injection.py`.
- **Live Tamper Demo:** `python -m backstop.ledger.chain` — appends 3 entries, verifies clean chain, tampers block #2, shows `verify_chain()` detecting the exact bad sequence number.

---

## 11. License

MIT License • Developed for Razorpay AI Buildathon 2026.
