# Backstop — Technical Architecture Document

**Track:** 03 — AI Revenue Recovery  
**Target:** Razorpay AI Buildathon 2026

---

## 1. System Overview

**Backstop** is an enterprise-grade, deterministic-policy-gated AI revenue recovery engine. When payments fail across credit/debit cards, UPI, netbanking, or recurring e-mandates, merchants typically either do nothing or blindly retry everything. Both extremes leak revenue, trigger issuer risk penalties, and harass customers.

Backstop establishes the competent middle path:
1. Deterministically diagnoses the exact root cause against Razorpay's published error taxonomy.
2. Evaluates winnability and determines permissible recovery actions inside a strict compliance cage (RBI E-mandate Framework 2026 + TRAI Commercial Communications Regulations).
3. Utilizes **Google Gemini** as a *chooser* (never an *actor*), constraining output to strict JSON schemas with monotonic fallback ladders toward inaction.
4. Executes actions through a **5-Wall Gated Executor** protected by SHA-256 idempotency keys.
5. Records every lifecycle transition into an append-only, tamper-evident SHA-256 hash-chained audit ledger.
6. Measures incremental revenue recovery against an un-intervened control group across a reproducible 1,000-case synthetic dataset.

---

## 2. End-to-End Pipeline Architecture

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
                    │  (source, step, reason) → RootCause      │
                    │  Exact map on 40+ Razorpay Error Reasons │
                    │  LLM fallback only for free-text (~2%)   │
                    └────────────────┬─────────────────────────┘
                                     │
        ╔════════════════════════════▼═════════════════════════╗
        ║  3. POLICY ENGINE — PRE-GATE CAGE (R01..R14)         ║
        ║  R01 Global Kill Switch    R08 DND / Consent         ║
        ║  R02 Risk Hard-Stop        R09 RBI Notice ≥24h       ║
        ║  R03 Terminal Cause        R10 RBI AFA Ceilings      ║
        ║  R04 Max 3 Attempts        R11 Promise-to-Pay Freeze ║
        ║  R05 Cool-off Windows      R12 Merchant Defect Cage  ║
        ║  R06 TRAI Quiet Hours IST  R13 Incentive Budget Cap  ║
        ║  R07 Daily Contact Cap     R14 Control Arm Isolation ║
        ╚════════════════════════════┬═════════════════════════╝
                                     │  PERMITTED_ACTIONS ⊆ ALL_ACTIONS
                    ┌────────────────▼─────────────────────────┐
                    │  4. DATA REDACTION LAYER (DPDP Act 2023) │
                    │  Strips PII (Names, Phones, Emails)      │
                    │  Discretizes amounts to bands (<₹500...) │
                    │  Fences untrusted notes in <untrusted>   │
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  5. PLANNER (Google Gemini API)          │
                    │  Strict JSON Schema Enforcement          │
                    │  2-Attempt Self-Repair Retry Loop        │
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
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │  8. EVALUATION & OPERATIONS CONSOLE      │
                    │  Two-Proportion Z-Test / 95% CI Lift     │
                    │  React Operations Console (4 Views)      │
                    └──────────────────────────────────────────┘
```

---

## 3. The Core Tenet

> **"The model is a chooser, not an actor. It picks from a set the policy engine already approved, and its pick is independently re-validated against the database record before anything executes. There is no code path in Backstop where an LLM output directly initiates money movement."**
