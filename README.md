# Backstop ⚡

<div align="center">

# BACKSTOP
### Deterministic Policy-Gated AI Revenue Recovery Engine for Razorpay

[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Console-React%2019%20%2B%20Vite%208-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-82%2F82%20Passing%20(100%25)-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![RBI E-mandate Framework](https://img.shields.io/badge/Compliance-RBI%202026%20%7C%20TRAI-0A85EA.svg)](docs/POLICY.md)
[![Audit Chain](https://img.shields.io/badge/Audit-SHA--256%20Hash%20Chain-8A2BE2.svg)](backstop/ledger/chain.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An enterprise-grade, high-throughput autonomous recovery engine for failed digital payments across Cards, UPI, Netbanking, and Recurring E-mandates.**  
*Operates inside a deterministic compliance cage with zero policy violations, strict four-eyes human oversight on high-risk cases, and cryptographic audit proofs.*

---

[**Executive Summary**](#1-executive-summary) •
[**Quickstart & Local Usage**](#2-quickstart--local-development-guide) •
[**Architecture & Pipeline**](#3-system-architecture--core-axioms) •
[**Engineering Restraint**](#4-where-we-chose-not-to-use-ai-engineering-restraint) •
[**Empirical Benchmark**](#5-empirical-evaluation-benchmark-n1000) •
[**15-Rule Compliance Cage**](#6-the-machine-executable-compliance-cage-15-rules) •
[**Enterprise Features**](#7-enterprise-platform-capabilities-backstop-20) •
[**Operations Console**](#8-operations-console-ui) •
[**API Reference**](#9-rest-api--webhook-directory) •
[**Verification Playbook**](#10-testing--chaos-engineering-playbook) •
[**Post-Mortem Log**](#11-engineering-integrity--post-mortem-log)

---

</div>

## 1. Executive Summary

In Indian digital commerce, payment failures represent a silent multi-crore margin drain across UPI, Credit/Debit cards, Netbanking, and recurring E-mandates. Merchants typically oscillate between two destructive extremes:

1. **The Inaction Trap (Do Nothing):** Abandoned checkouts and failed mandate renewals directly become permanent customer churn and lost Gross Merchandise Value (GMV).
2. **The Naive Retry Trap (Blind Retries):** Retrying every failure blindly creates massive SMS/WhatsApp communication bills, violates TRAI anti-harassment quiet hours, triggers NPCI and bank issuer rate penalties, and creates severe non-compliance exposure against the **RBI Digital Payments E-mandate Framework (21 April 2026)**.

**Backstop resolves this false dichotomy.** It intercepts payment failures from Razorpay webhooks in real time, deterministically maps failure taxonomy codes against 40+ known bank decline causes, cages all actions within 15 machine-executable statutory rules, uses **Google Gemini** as a constrained chooser over pre-approved action subsets, executes through a **5-Wall Gated Executor**, and immutably records every lifecycle transition into an append-only **SHA-256 cryptographic audit chain**.

### Key Business & Technical Metrics (Seeded N=1,000 Benchmark)

| Key Metric | Naive Retry-All ×3 | Backstop Autonomous Engine ⚡ | Business Advantage |
|---|---|---|---|
| **Gross Revenue Recovered** | ₹12,95,854.00 | **₹19,38,767.00** | **+₹6,42,913.00 (+49.6%)** higher recovery |
| **Incremental Margin over Control** | ₹1,22,984.00 | **₹11,33,609.11** | **9.2× higher incremental profit** |
| **Causal Recovery Lift (95% CI)** | +1.7 pp | **+19.1% [+13.5%, +24.8%]** | Statistically significant ($p = 1.10 \times 10^{-7}$) |
| **Customer Messages Dispatched** | 2,000 comms | **235 comms** | **88.2% reduction in customer spam** |
| **Contacts per ₹1,000 Recovered** | 1.54 messages | **0.12 messages** | **12.8× higher communication efficiency** |
| **Compliance & Policy Violations** | 690 violations | **0 violations** | **100% cage integrity held** |
| **Hard-Stop Cases Auto-Actioned** | 42 breaches | **0 breaches** | **100% AML/risk cases escalated to human** |
| **Median Time to Recovery** | 28.1 hours | **20.9 hours** | **25.6% faster lifecycle resolution** |

---

## 2. Quickstart & Local Development Guide

Backstop is engineered to run seamlessly on local developer workstations (macOS, Linux, and Windows) with zero cloud dependencies required.

### 2.1 Prerequisites

Before setting up Backstop, ensure your environment has:
- **Python:** `3.11`, `3.12`, or `3.14` installed (`python --version`)
- **Node.js & npm:** Node `20+` and npm `10+` (`node -v && npm -v`)
- **Git:** Installed and configured (`git --version`)
- *(Optional)* **Redis:** `6.0+` for distributed multi-pod lock testing. If absent, Backstop automatically activates its built-in in-memory thread-safe lock fallback.

---

### 2.2 Repository Setup & Environment Configuration

```bash
# 1. Clone the repository
git clone https://github.com/nika619/BackStop-.git
cd BackStop-

# 2. Set up Python virtual environment (Recommended)
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Install dependencies for Backend & Frontend
pip install -r requirements.txt
cd console && npm install && cd ..
```

#### Configure Environment Variables (`.env`)

Copy the provided `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Environment Variable | Default Value | Description |
|---|---|---|
| `PORT` | `8000` | FastAPI server listening port. |
| `HOST` | `0.0.0.0` | FastAPI server network binding. |
| `ENVIRONMENT` | `development` | Runtime environment (`development` / `production`). |
| `DRY_RUN` | `true` | When `true`, external Razorpay API debits are safely mocked with logged payloads. |
| `DATABASE_URL` | `sqlite:///./data/backstop.db` | Database connection string (SQLite file or PostgreSQL). |
| `GEMINI_API_KEY` | *(optional)* | Google Gemini API Key. If empty or quota-limited, system automatically utilizes deterministic heuristic fallback ladder. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini foundation model identifier. |
| `RAZORPAY_KEY_ID` | `rzp_test_placeholder_key_id` | Razorpay API key identifier. |
| `RAZORPAY_KEY_SECRET` | `dummy_secret_key_placeholder` | Razorpay API secret key. |
| `RAZORPAY_WEBHOOK_SECRET`| `dummy_webhook_secret_for_testing_only` | Secret key for verifying HMAC-SHA256 webhook signatures. |
| `QUIET_HOURS_START_IST` | `9` | TRAI quiet hours boundary start (09:00 IST). |
| `QUIET_HOURS_END_IST` | `21` | TRAI quiet hours boundary end (21:00 IST). |
| `MAX_ATTEMPTS` | `3` | Maximum automated retry attempts permitted per payment. |
| `INCENTIVE_BUDGET_INR` | `50000` | Merchant promotional incentive pool cap (in INR). |

---

### 2.3 Running the Application (3 Launch Modes)

#### Mode A: Single-Command Automated Launch (Recommended)

Backstop includes an enterprise orchestrator that initializes the database, seeds the 1,000-case benchmark dataset, starts the FastAPI backend, boots the Vite Operations Console, and opens your default web browser automatically:

```bash
python run.py
```

*Output summary:*
```
======================================================================
⚡ LAUNCHING BACKSTOP 2.0 ENTERPRISE REVENUE RECOVERY ENGINE
   Razorpay AI Buildathon 2026 • Track 03
======================================================================
1️⃣ Initializing database & seeding benchmark dataset...
2️⃣ Starting FastAPI API Server (http://localhost:8000)...
3️⃣ Starting Operations Console UI (http://localhost:5173)...
🌐 Opening Operations Console in your default browser...
✅ BACKSTOP IS LIVE AND READY!
   • API Server & Swagger Docs: http://localhost:8000/docs
   • Operations Console UI:     http://localhost:5173
```

#### Mode B: Make Automation (macOS / Linux / WSL)

```bash
make setup    # Installs Python and Node dependencies
make test     # Runs all 82 unit, chaos, and integration tests
make eval     # Runs the 1,000-case statistical benchmark and generates artifacts
make demo     # Single-command launcher (seeds DB, runs backend and frontend)
make start    # Starts the application
make clean    # Cleans test cache, coverage, and build artifacts
```

#### Mode C: Independent Microservices (Multi-Terminal)

If you prefer running frontend and backend independently in dedicated terminals:

**Terminal 1 — Backend API Service:**
```bash
python -m uvicorn backstop.api:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive API Documentation (Swagger): `http://localhost:8000/docs`
- Alternative OpenAPI UI (ReDoc): `http://localhost:8000/redoc`
- System Health Endpoint: `http://localhost:8000/api/health`

**Terminal 2 — React Operations Console:**
```bash
cd console
npm run dev
```
- Operations Console UI: `http://localhost:5173`

---

### 2.4 Verifying the Local Installation

#### 1. Execute the Automated Test Suite (82/82 Passing)

Run the comprehensive test suite verifying compliance, chaos scenarios, prompt injection defense, bank outage telemetry, and idempotency:

```bash
python -m pytest -v --cov=backstop
```

#### 2. Reproduce the 1,000-Case Empirical Benchmark

Execute the reproducible synthetic benchmark with causal 80/20 A/B split:

```bash
python -m backstop.eval.report
```
*Generates formatted terminal summary and updates the evidence artifact at [`docs/evidence/eval_run.txt`](docs/evidence/eval_run.txt).*

#### 3. Test the Cryptographic Ledger & Tamper Detection CLI

Run the cryptographic audit chain verification and tamper demonstration tool:

```bash
python -m backstop.ledger.chain
```
*Demonstrates SHA-256 block creation, verifies a clean chain, injects a deliberate payload tamper on block #2, and proves `verify_chain()` pinpoints the exact tampered sequence index.*

---

### 2.5 Simulating Live Inbound Razorpay Webhooks Locally

Backstop enforces strict HMAC-SHA256 cryptographic signature validation on inbound webhook payloads. You can simulate inbound events using the following snippets:

#### Ingest a `payment.failed` Event (Initiates Recovery)

```bash
python -c "
import hmac, hashlib, httpx

secret = b'dummy_webhook_secret_for_testing_only'
payload = b'{\"entity\":\"event\",\"event\":\"payment.failed\",\"contains\":[\"payment\"],\"payload\":{\"payment\":{\"entity\":{\"id\":\"pay_live_test_001\",\"order_id\":\"order_live_test_001\",\"amount\":49900,\"currency\":\"INR\",\"status\":\"failed\",\"method\":\"upi\",\"error_code\":\"BAD_REQUEST_ERROR\",\"error_description\":\"Payment failed due to customer drop-off\",\"error_source\":\"customer\",\"error_step\":\"payment_authentication\",\"error_reason\":\"payment_cancelled_by_user\",\"notes\":{\"merchant_id\":\"merch_ecommerce_01\"}}}}}'

sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
resp = httpx.post('http://localhost:8000/webhooks/razorpay', content=payload, headers={'X-Razorpay-Signature': sig, 'Content-Type': 'application/json'})
print(f'Response [{resp.status_code}]: {resp.json()}')
"
```

#### Ingest a `payment.captured` Event (Closes Recovery Lifecycle)

```bash
python -c "
import hmac, hashlib, httpx

secret = b'dummy_webhook_secret_for_testing_only'
payload = b'{\"entity\":\"event\",\"event\":\"payment.captured\",\"contains\":[\"payment\"],\"payload\":{\"payment\":{\"entity\":{\"id\":\"pay_live_test_001\",\"order_id\":\"order_live_test_001\",\"amount\":49900,\"currency\":\"INR\",\"status\":\"captured\",\"method\":\"upi\",\"notes\":{\"merchant_id\":\"merch_ecommerce_01\"}}}}}'

sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
resp = httpx.post('http://localhost:8000/webhooks/razorpay', content=payload, headers={'X-Razorpay-Signature': sig, 'Content-Type': 'application/json'})
print(f'Response [{resp.status_code}]: {resp.json()}')
"
```

---

## 3. System Architecture & Core Axioms

Backstop follows an immutable architectural tenet designed for mission-critical financial systems:

> **The Core Architecture Axiom:**  
> *"The AI model is a chooser, not an actor. It picks from a finite action set that the deterministic policy engine has already validated and approved. Every pick is independently re-validated against the database record before anything executes. There is no code path in Backstop where an LLM output directly initiates money movement or customer communication."*

```
                                  INBOUND INGEST GATEWAY
                      ┌──────────────────────────────────────────────┐
                      │  • Razorpay Signed Webhook (HMAC-SHA256)     │
                      │  • Immediate HTTP 202 Accepted (<15ms ACK)   │
                      │  • Durable DB-Backed QueueJob (Persistence)  │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                                  DETERMINISTIC DIAGNOSIS
                      ┌──────────────────────────────────────────────┐
                      │  • 40+ Razorpay Error Codes exact map        │
                      │  • (error_source, step, reason) → RootCause  │
                      │  • LLM fallback strictly for ~2% free text   │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                                  POLICY PRE-GATE CAGE (R01..R15)
         ╔══════════════════════════════════════════════════════════════════╗
         ║  • R01 Kill Switch               • R08 DND / Consent Check       ║
         ║  • R02 AML / Risk Hard Stop      • R09 RBI Notice ≥ 24h Receipt  ║
         ║  • R03 Terminal Instrument Block • R10 RBI AFA Tier Ceilings     ║
         ║  • R04 Attempt Limit (Max 3)     • R11 Promise-to-Pay Freeze     ║
         ║  • R05 Cool-off Windows (0h/4h)  • R12 Merchant Bug Isolation    ║
         ║  • R06 TRAI Quiet Hours IST      • R13 Promotional Budget Cap    ║
         ║  • R07 Daily Contact Cap (Max 2) • R14 Causal Arm Isolation      ║
         ║  • R15 Bank Telemetry & Dynamic Outage Cool-off                  ║
         ║  OUTPUT: PERMITTED_ACTIONS ⊆ ALL_ACTIONS                         ║
         ╚═══════════════════════════════════╤══════════════════════════════╝
                                             │
                                             ▼
                                  DATA REDACTION LAYER (DPDP 2023)
                      ┌──────────────────────────────────────────────┐
                      │  • Strips customer PII (Name, Phone, Email)  │
                      │  • Discretizes amounts to non-invertible bands│
                      │  • Untrusted free text wrapped in XML cages  │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                                  PLANNER (Google Gemini API)
                      ┌──────────────────────────────────────────────┐
                      │  • Enforces strict Pydantic JSON Schema      │
                      │  • Constrained to PERMITTED_ACTIONS set      │
                      │  • 2-attempt self-repair retry loop          │
                      │  • Monotonic fallback ladder: safest()       │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                                  5-WALL GATED EXECUTOR
         ╔══════════════════════════════════════════════════════════════════╗
         ║  Wall 1: Global & Merchant Kill Switch Verification              ║
         ║  Wall 2: Post-Gate Re-Validation against active DB record        ║
         ║  Wall 3: Tool Spend Cap Enforcement                              ║
         ║  Wall 4: Four-Eyes Human Approval on high-risk / AML cases       ║
         ║  Wall 5: Distributed Redis SETNX Idempotency Lock                ║
         ╚═══════════════════════════════════╤══════════════════════════════╝
                                             │
                                             ▼
                                  CRYPTOGRAPHIC AUDIT LEDGER
                      ┌──────────────────────────────────────────────┐
                      │  • Append-only SHA-256 Hash Chain            │
                      │  • Current Hash = SHA256(prev_hash + payload)│
                      │  • Instant zero-trust tamper detection       │
                      └──────────────────────────────────────────────┘
```

### Two-Phase Stateful Lifecycle Closure

In naive systems, recovery engines dispatch an action (e.g., sending a payment link) and prematurely count the entire invoice as "recovered". Backstop implements an immutable, two-phase financial state machine:

```
[payment.failed] ──► [case_opened] ──► [action_dispatched] ──┐
                                             │               │ Inbound Webhook
                                             ▼               │ (payment.captured / order.paid)
                                     (recovered_paise = 0)   ▼
                                                    [recovered] (recovered_paise = amount)
```

1. **Phase 1 (Action Dispatch):** When an action executes (e.g., `SWITCH_RAIL_LINK`, `NUDGE_CHECKOUT`), the case transitions to `action_dispatched`. Recovered amount remains strictly **`₹0.00`**.
2. **Phase 2 (Verified Inbound Settlement):** Only when Razorpay delivers a verified, signed `payment.captured` or `order.paid` webhook does Backstop transition the case to `recovered` and credit `recovered_paise`.

---

## 4. Where We Chose NOT to Use AI (Engineering Restraint)

The highest indicator of engineering seniority is knowing **when not to use AI**. Many AI solutions blindly pass every decision to an LLM. In Backstop, AI is purposefully restricted:

```
┌───────────────────────────────────────────┬───────────────────────────────┬────────────────────────────────────────────────────────┐
│ Pipeline Component                        │ Technology Chosen             │ Architectural Rationale                                │
├───────────────────────────────────────────┼───────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Root Cause Classification (98% volume) │ Deterministic Lookup Table    │ Razorpay provides structured error codes. A dictionary │
│                                           │ (backstop/diagnose/taxonomy)  │ lookup is O(1), zero-cost, 100% deterministic,         │
│                                           │                               │ and has zero latency. LLM used only for free text.     │
├───────────────────────────────────────────┼───────────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Regulatory & Statutory Compliance      │ Deterministic Predicate Cage  │ Regulations (RBI E-mandate, TRAI quiet hours) are hard │
│                                           │ (backstop/policy/engine)      │ legal boundaries. LLM probabilistic reasoning cannot be│
│                                           │                               │ legally audited or guaranteed against hallucinations.  │
├───────────────────────────────────────────┼───────────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Backoff Timing & Retry Calculations    │ Arithmetic Function           │ Cool-off windows (0h, 4h, 48h) and payday priors       │
│                                           │ (backstop/policy/engine)      │ follow deterministic math. Prompting an LLM for time   │
│                                           │                               │ calculations is wasteful, fragile, and non-reproducible│
├───────────────────────────────────────────┼───────────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. Financial Transaction Authority        │ 5-Wall Programmatic Gates     │ LLMs hallucinate actions. No code path permits an LLM  │
│                                           │ (backstop/execute/executor)   │ to execute money movement without multi-gate validation│
├───────────────────────────────────────────┼───────────────────────────────┼────────────────────────────────────────────────────────┤
│ 5. Audit Logging & Verification           │ SHA-256 Hash Chain            │ Cryptographic chaining mathematically guarantees ledger│
│                                           │ (backstop/ledger/chain)       │ tamper detection without subjective model evaluation.  │
└───────────────────────────────────────────┴───────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 5. Empirical Evaluation Benchmark (N=1,000)

Backstop is validated on a 1,000-case seeded synthetic benchmark (`seed = 20260901`) simulating the Indian digital payments ecosystem across Credit Cards, Debit Cards, UPI, Netbanking, and Recurring E-mandates.

To eliminate selection bias, Backstop incorporates a **held-out 20% control arm** within its own evaluation stream, alongside independent full-corpus simulations of **Do Nothing** and **Naive Retry-All ×3**.

### Benchmark Comparison Matrix

```
=============================================================================================================
                                     EMPIRICAL BENCHMARK EVALUATION (N=1,000)
=============================================================================================================
Metric                                  Do Nothing (Control)      Retry-All ×3 (Naive)     Backstop (Agent) ⚡
-------------------------------------------------------------------------------------------------------------
Total Corpus Cases                      1,000                     1,000                    1,000
Backstop Arm Split                      —                         —                        810 treat / 190 ctrl
Gross Revenue Recovered                 ₹11,72,870.00             ₹12,95,854.00            ₹19,38,767.00
Net Incremental Margin over Baseline    ₹0.00                     ₹1,22,984.00             ₹11,33,609.11
Causal Recovery Lift (95% CI)           Baseline                  +1.7 pp                  +19.1% [+13.5%, +24.8%]
Overall Recovery Rate                   15.8%                     17.5%                    27.6%
Customer Contacts Dispatched            0 messages                2,000 messages           235 messages
Anti-Spam Contact Reduction             Baseline                  0.0%                     88.2% reduction
Contacts per ₹1,000 Recovered           0.00                      1.54                     0.12 (12.8× more efficient)
Policy Violations Recorded              0                         690 violations           0 (Cage Held Flawlessly)
Hard-Stop AML Cases Auto-Actioned       0                         42 breaches              0 (100% Escrowed to Human)
Median Time to Recovery                 52.4 hours                28.1 hours               20.9 hours
=============================================================================================================
Statistical Significance: Two-proportion z-score = 5.308, p-value = 1.10 × 10⁻⁷. 
Reproducible Artifact: docs/evidence/eval_run.txt
```

### Statistical Analysis & Key Insights

1. **Massive Incremental Margin:** Backstop extracts **₹11,33,609.11** in net new incremental revenue above the organic recovery baseline, outperforming naive retries by over 9.2×.
2. **Statistically Significant Causal Lift:** The two-proportion z-test confirms a lift of **+19.1%** with a 95% confidence interval of `[+13.5%, +24.8%]` ($p = 1.10 \times 10^{-7}$), proving the lift is strictly causal and not stochastic noise.
3. **88.2% Contact Spam Elimination:** Naive retries send 2,000 spam communications across 1,000 cases. Backstop dispatches only 235 targeted nudges, recovering 49.6% more gross money while preserving customer goodwill and avoiding TRAI carrier penalties.
4. **Zero Regulatory Breaches:** The deterministic compliance cage blocked all 690 illegal actions that naive systems executed, maintaining a 0-violation record across all 15 rules.

---

## 6. The Machine-Executable Compliance Cage (15 Rules)

All recovery actions must satisfy the 15 machine-executable predicates defined in [`docs/POLICY.md`](docs/POLICY.md):

| Rule ID | Name & Scope | Regulatory / Operational Citation | Machine-Executable Specification |
|---|---|---|---|
| **R01** | **Global / Tenant Kill Switch** | Fintech Trust & Operational Safety Standard | If `kill_switch == True` (global or per-MID), returns `permitted = {NO_ACTION}`. |
| **R02** | **AML & Risk Hard-Stop** | Prevention of Money Laundering Act (PMLA) 2002 | `payment_risk_check_failed`, compliance flags route strictly to `ESCALATE_HUMAN`. Zero automated recovery permitted. |
| **R03** | **Terminal Cause Block** | Card Network & NPCI Terminal Decline Guidelines | Expired cards, invalid VPAs, or blocked accounts are barred from `RETRY_SAME_RAIL`. |
| **R04** | **Attempt Limit Cap** | Card Network Rate Limiting & Customer Protection | Programmatic retries blocked if `attempt_no >= max_attempts` (default: 3). |
| **R05** | **Cool-off Backoff Windows** | Issuer Decline Processing Guidelines | Enforces mandatory cool-offs between retries: 0h for Attempt 0→1, 4h for 1→2, 48h for 2→3. |
| **R06** | **TRAI Quiet Hours (IST)** | TRAI Telecom Commercial Communications Customer Preference Reg. | Blocks outbound customer nudges outside **09:00–21:00 IST** (`UTC+05:30`). Explicit timezone conversion. |
| **R07** | **Daily Contact Cap** | Anti-Harassment Communication Standard | Max 2 customer communications allowed per customer reference per calendar day. |
| **R08** | **DND / Consent Registry** | National Do Not Call (NDNC) Registry & DPDP Act 2023 | Customer contact is hard-blocked if customer is marked DND or consent revoked. |
| **R09** | **RBI Notice & Delivery Receipt** | **RBI Digital Payments E-mandate Framework (21 April 2026)** | Recurring mandate debits require verified delivery receipt (`DELIVERED`) and pre-debit notice sent $\ge 24$h prior. |
| **R10** | **RBI AFA Ceiling Ceilings** | **RBI Digital Payments E-mandate Framework (21 April 2026)** | ₹15,000 default ceiling; ₹1,00,000 elevated ceiling for Insurance, Mutual Funds, Credit Card bills. |
| **R11** | **Promise-to-Pay Grace Freeze**| Ethical Collections & Fair Practices Code | If customer committed a future payment date (`promise_to_pay_at > now`), chasing is frozen. |
| **R12** | **Merchant Configuration Isolation**| Merchant Integration SLA Standard | Integration defects (`order_amount_mismatch`, `validation_error`) alert merchant; customer contact barred. |
| **R13** | **Incentive Budget Pool Cap** | Corporate Treasury Risk Policy | Rail-switch promotional discounts capped per isolated merchant budget (`incentive_budget_paise`). |
| **R14** | **Causal Arm Isolation** | Scientific Experimentation Hygiene | 20% held-out control group strictly observes without intervention (`NO_ACTION`). |
| **R15** | **Live Bank Telemetry & Outage**| Live Banking Network Telemetry Standard | If bank success rate drops below 70% (e.g., HDFC outage), retries are delayed by +2h cool-off. |

---

## 7. Enterprise Platform Capabilities (Backstop 2.0)

Backstop 2.0 introduces production-grade distributed architecture patterns:

### 1. Multi-Tenant Isolation (MID Partitioning)
- Operates with strict tenant data isolation by `merchant_id` (e.g., `merch_ecommerce_01`, `merch_saas_sub_02`).
- Each merchant maintains independent configuration for quiet hours, retry caps, promotional incentive budgets, and auto-recovery toggles.

### 2. Durable DB-Backed Job Queue with Crash Recovery
- Replaced volatile in-memory queues with persistent `QueueJob` database records.
- If the application pod crashes or is terminated by Kubernetes OOM killers, the background worker automatically invokes `recover_interrupted_jobs()` on boot, resuming interrupted recovery jobs without dropping transactions.

### 3. Distributed Redis Idempotency Locks
- Multi-pod safe concurrency control using Redis `SETNX` distributed locks (`lock:idempotency:{mid}:{payment_id}:{attempt_no}`, TTL 60s).
- Gracefully falls back to thread-safe memory locks if Redis is not configured in local environments.

### 4. Real Razorpay Programmatic Tool Execution
- Dispatches genuine Razorpay API requests:
  - **Payment Links:** Generates hosted payment URLs with automatic expiry.
  - **Recurring Subscriptions:** Re-submits tokenized debits with pre-debit authorization flags.
  - **Order Cancellation:** Cancels legacy orders (`POST /v1/orders/{order_id}/cancel`) during rail switches to prevent accidental double-charging.
- Full support for `X-Razorpay-Idempotency-Header` to guarantee bank-level idempotency.

### 5. DPDP Act 2023 Redaction Layer & Prompt Injection Defense
- Strips customer names, phone numbers, and email addresses before assembling context for the LLM planner.
- Discretizes transaction amounts into coarse non-invertible brackets (`< ₹500`, `₹500–₹2,000`, `₹2,000–₹10,000`, `> ₹10,000`).
- Untrusted user notes are encapsulated inside `<untrusted>` XML fencing, preventing jailbreak attacks and instruction overrides (validated in `tests/test_prompt_injection.py`).

---

## 8. Operations Console UI

The Backstop Operations Console is a high-performance React 19 + Tailwind CSS single-page application providing four mission-critical command screens:

<div align="center">

| Screen | Operational Purpose |
|---|---|
| **1. Cohort & Benchmark Analytics** | Visualizes 3-way A/B performance, incremental revenue lift, 95% confidence intervals, z-score hypothesis validation, and contact efficiency metrics. |
| **2. Operations Case Timeline** | Real-time case explorer with multi-tenant filtering (MID), status tracking, root cause categorization, slide-over detail drawer, and **Four-Eyes Human Approval** action buttons. |
| **3. Dynamic Policy & Outage Controls** | Interactive control room for per-merchant configuration: adjust quiet hours, modify retry attempt caps, update incentive budgets, and simulate live bank outages (e.g. inject HDFC downtime to test R15). |
| **4. Cryptographic Security & Audit Ledger** | Real-time tamper verification of the SHA-256 ledger chain, interactive tamper injection demo, DPDP redaction inspector, and STRIDE threat model documentation. |

</div>

---

## 9. REST API & Webhook Directory

FastAPI serves the Backstop REST API at `http://localhost:8000`. Full OpenAPI / Swagger documentation is available at `http://localhost:8000/docs`.

### Core Endpoints

| Method | Endpoint | Description | Key Parameters / Request Body |
|---|---|---|---|
| `GET` | `/api/health` | Service health, active policy version, and kill switch status. | None |
| `GET` | `/api/benchmark` | Seeded 1,000-case evaluation report and lift statistics. | `recompute: bool` (optional) |
| `GET` | `/api/cases` | Paginated case explorer with multi-filter capability. | `merchant_id`, `status`, `cohort_arm`, `root_cause`, `limit`, `offset` |
| `GET` | `/api/cases/{case_id}` | Detailed case inspection, event history, and audit log. | `case_id: str` |
| `POST` | `/api/cases/{case_id}/approve` | Four-eyes human approval for high-risk / escalated cases. | `case_id: str` |
| `POST` | `/api/cases/{case_id}/override`| Manual operator override of proposed action. | `case_id: str`, `body: { action, reason }` |
| `GET` | `/api/policies` | Retrieve multi-tenant policies across all merchants. | None |
| `PUT` | `/api/policies/{merchant_id}` | Update merchant policy parameters (quiet hours, caps). | `merchant_id: str`, `body: MerchantPolicyUpdate` |
| `GET` | `/api/kill-switch` | Inspect global emergency kill switch state. | None |
| `POST` | `/api/kill-switch` | Toggle global emergency kill switch. | `body: { enabled: bool }` |
| `GET` | `/api/ledger` | Retrieve cryptographic audit ledger entries. | `limit: int`, `offset: int` |
| `GET` | `/api/ledger/verify` | Verify the cryptographic SHA-256 hash chain integrity. | None |
| `POST` | `/api/ledger/tamper-demo` | Deliberately alter block #2 to demonstrate tamper detection.| None |
| `GET` | `/api/bank-health` | Retrieve live banking network health telemetry. | None |
| `POST` | `/api/bank-health/{bank_code}`| Set simulated bank success rate (trigger outage cool-off).| `bank_code: str`, `body: { success_rate: float }` |
| `POST` | `/webhooks/razorpay` | Inbound signed Razorpay webhook handler (<15ms ACK). | Header: `X-Razorpay-Signature`, Body: Razorpay event |

---

## 10. Testing & Chaos Engineering Playbook

Backstop maintains an exhaustive test suite of **82 automated tests** covering unit, integration, chaos, and security vectors:

```bash
# Run all tests with coverage report
python -m pytest -v --cov=backstop

# Run policy engine compliance tests (all 15 rules)
python -m pytest tests/test_policy.py -v

# Run RBI E-mandate 2026 delivery receipt compliance tests
python -m pytest tests/test_rbi_delivery_receipt.py -v

# Run chaos engineering and race condition tests
python -m pytest tests/test_chaos.py -v

# Run prompt injection defense tests
python -m pytest tests/test_prompt_injection.py -v

# Run cryptographic ledger and tamper detection tests
python -m pytest tests/test_ledger.py -v

# Run multi-tenant isolation tests
python -m pytest tests/test_multitenancy.py -v
```

### Test Suite Directory

```
tests/
├── test_bank_health.py           # Bank outage telemetry & R15 outage cool-off delay
├── test_chaos.py                 # Duplicate webhooks, empty permitted sets, fallback ladders
├── test_classifier.py            # Error taxonomy classifier accuracy
├── test_classifier_extended.py   # Comprehensive coverage of 40+ Razorpay error codes
├── test_executor.py              # 5-wall gated executor validation and action dispatch
├── test_idempotency.py           # SHA-256 idempotency key collision and deduplication
├── test_ledger.py                # SHA-256 append-only hash chain and tamper localization
├── test_multitenancy.py          # Tenant isolation across merchants (MIDs)
├── test_policy.py                # Exhaustive validation of compliance rules R01 through R15
├── test_prompt_injection.py      # Untrusted note fencing and prompt injection defense
├── test_razorpay_client.py       # Programmatic Razorpay API client integration
├── test_rbi_delivery_receipt.py  # RBI 2026 24h pre-debit notice and DELIVERED receipt checks
├── test_redact.py                # DPDP Act 2023 PII sanitization and amount discretization
├── test_redis_lock.py            # Distributed SETNX locking and in-memory fallback
└── test_taxonomy.py              # Root cause mappings and terminal error classification
```

---

## 11. Engineering Integrity & Post-Mortem Log

Enterprise software requires full disclosure of engineering challenges and failure modes encountered during development:

### 1. The UTC Timezone Bug in TRAI Quiet Hours
- **Symptom:** Outbound customer nudges were permitted during Indian night hours (e.g. 03:00 AM IST).
- **Root Cause:** Host system evaluated `datetime.now()` in UTC. A failure at 22:30 UTC was evaluated as 22:30 instead of 04:00 AM IST the next morning.
- **Remediation:** Converted all time checks to explicitly consume an injected `now: datetime` translated to Indian Standard Time (`UTC+05:30`) via `backstop.policy.calendar.to_ist`. Regression tests enforced via `freezegun` in `tests/test_policy.py`.

### 2. Webhook Replay Race Condition
- **Symptom:** Concurrent webhook deliveries for the same failed payment resulted in duplicate case initialization.
- **Root Cause:** Application-level check-then-insert logic allowed simultaneous requests to pass deduplication before committing.
- **Remediation:** Enforced a database unique constraint on `PaymentEvent.event_id` and deployed Wall 5 SHA-256 idempotency hashing (`payment_id | action | attempt_no`).

### 3. Gemini Fallback Self-Audit Discovery
- **Symptom:** Benchmark tests were generating valid results, but outbound network monitoring recorded zero calls to the Gemini API.
- **Root Cause:** The `.env` file had an empty `GEMINI_API_KEY`, causing the system to quietly route all planning decisions to the deterministic heuristic fallback ladder.
- **Remediation:** Wired genuine Gemini API keys, verified live model calls, and added explicit terminal warning banners when operating in heuristic fallback mode. Proved that the compliance cage held identically under both LLM and fallback operation.

### 4. Premature Lifecycle Settlement Elimination
- **Symptom:** Early prototypes marked cases as `recovered` at the moment an action was dispatched, recording recovered revenue before the user paid.
- **Root Cause:** Lack of an intermediate state between action trigger and actual payment settlement.
- **Remediation:** Implemented the two-phase lifecycle (`action_dispatched` with `recovered_paise = 0`), requiring an inbound signed `payment.captured` webhook before transitioning to `recovered`.

---

## 12. Project Structure

```
BackStop-/
├── README.md                     # Enterprise System Documentation
├── LICENSE                       # MIT Open Source License
├── Makefile                      # Standard CLI automation targets
├── run.py                        # Single-command orchestrator & launcher
├── requirements.txt              # Python production & test dependencies
├── pyproject.toml                # Project metadata & tool configuration
├── .env.example                  # Environment configuration template
│
├── backstop/                     # Core Revenue Recovery Engine
│   ├── api.py                    # FastAPI server, REST routes & lifecycle hooks
│   ├── database.py               # Database engine, session provider & seeders
│   ├── models.py                 # SQLModel & Pydantic domain models
│   │
│   ├── diagnose/                 # Root Cause Diagnosis
│   │   ├── classifier.py         # Deterministic classifier & LLM fallback
│   │   ├── taxonomy.py           # Razorpay 40+ error code mappings
│   │   └── bank_health.py        # Live bank telemetry & health scoring
│   │
│   ├── policy/                   # Compliance & Telemetry Cage
│   │   ├── engine.py             # Machine-executable rules R01..R15
│   │   └── calendar.py           # IST timezone normalization
│   │
│   ├── planner/                  # Safe Planning Engine
│   │   ├── planner.py            # Gemini API integration & schema enforcement
│   │   └── redact.py             # DPDP Act 2023 PII scrubber & amount discretizer
│   │
│   ├── execute/                  # 5-Wall Gated Executor
│   │   ├── executor.py           # 5-wall validation gates
│   │   ├── registry.py           # Programmatic Razorpay API dispatchers
│   │   └── lock.py               # Redis SETNX distributed locking
│   │
│   ├── ingest/                   # High-Throughput Ingestion
│   │   ├── webhook.py            # Signed HMAC-SHA256 webhook handler
│   │   ├── queue_worker.py       # Durable DB-backed job worker & crash recovery
│   │   └── batch.py              # Batch CSV / JSONL import utilities
│   │
│   ├── ledger/                   # Cryptographic Audit Ledger
│   │   └── chain.py              # SHA-256 append-only hash chain & tamper detection
│   │
│   └── eval/                     # Empirical Evaluation
│       ├── generator.py          # Seeded synthetic payments generator
│       ├── simulator.py          # Causal outcome simulation engine
│       ├── baselines.py          # Do-Nothing & Retry-All baseline strategies
│       └── report.py             # Z-test statistical benchmark runner
│
├── console/                      # Operations Console (Frontend)
│   ├── src/
│   │   ├── App.jsx               # Navigation & screen layout
│   │   ├── components/
│   │   │   ├── Header.jsx        # Global status, MID switcher, kill switch
│   │   │   ├── CohortScreen.jsx  # A/B evaluation benchmark & lift visualizer
│   │   │   ├── TimelineScreen.jsx# Recovery operations timeline & detail drawer
│   │   │   ├── PolicyScreen.jsx  # Multi-tenant policy & bank outage controls
│   │   │   └── SecurityScreen.jsx# Tamper ledger & DPDP redaction inspector
│   │   └── index.css             # Tailwind CSS tokens
│   └── package.json              # React 19, Vite 8, Tailwind CSS dependencies
│
├── docs/                         # Technical Documentation
│   ├── ARCHITECTURE.md           # Deep-dive architecture design document
│   ├── POLICY.md                 # 15 compliance rules formal specification
│   ├── THREAT_MODEL.md           # STRIDE security & risk analysis
│   ├── EVALUATION.md             # Benchmark methodology & statistical rigor
│   └── evidence/
│       └── eval_run.txt          # Reproducible evaluation run output
│
└── tests/                        # 82 Automated Unit & Chaos Tests
```

---

## 13. Author & License

- **Lead Architect & Developer:** [nika619](https://github.com/nika619)
- **Repository:** [https://github.com/nika619/BackStop-](https://github.com/nika619/BackStop-)
- **Hackathon Track:** Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery
- **License:** MIT License. See [LICENSE](LICENSE) for full details.
