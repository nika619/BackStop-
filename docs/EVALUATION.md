# Backstop — Evaluation Methodology & Statistical Framework

## 1. Experimental Setup & Synthetic Prior Disclosure

> **Integrity Notice:** All evaluation data is synthetically generated using a seeded pseudo-random number generator (`seed = 20260901`) across 1,000 cases. We state our latent recovery probabilities and uplift multipliers explicitly as assumptions.

### Cause Mix Priors:
- Insufficient funds: 22%
- Authentication failed: 14%
- Payment timed out: 11%
- Gateway technical error: 9%
- Payment cancelled by user: 9%
- Bank unavailable: 7%
- Card expired / invalid: 10%
- Other (Risk check, International, Validation): 18%

---

## 2. Statistical Methodology

### Deterministic Arm Allocation:
$$h = \text{SHA256}(\text{payment\_id}) \pmod{100}$$
- $h < 20 \implies \text{Control Arm (20\%)}$
- $h \ge 20 \implies \text{Treatment Arm (80\%)}$

### Hypothesis Testing (Two-Proportion Z-Test):
$$\hat{p}_1 = \frac{X_{\text{treatment}}}{N_{\text{treatment}}}, \quad \hat{p}_2 = \frac{X_{\text{control}}}{N_{\text{control}}}$$
$$\hat{p}_{\text{pooled}} = \frac{X_{\text{treatment}} + X_{\text{control}}}{N_{\text{treatment}} + N_{\text{control}}}$$
$$\text{SE}_{\text{pooled}} = \sqrt{\hat{p}_{\text{pooled}}(1 - \hat{p}_{\text{pooled}})\left(\frac{1}{N_{\text{treatment}}} + \frac{1}{N_{\text{control}}}\right)}$$
$$Z = \frac{\hat{p}_1 - \hat{p}_2}{\text{SE}_{\text{pooled}}}$$

### 95% Confidence Interval:
$$\text{CI}_{95} = (\hat{p}_1 - \hat{p}_2) \pm 1.96 \cdot \sqrt{\frac{\hat{p}_1(1-\hat{p}_1)}{N_{\text{treatment}}} + \frac{\hat{p}_2(1-\hat{p}_2)}{N_{\text{control}}}}$$

---

## 3. Results Summary (N=1,000)

| Metric | Do Nothing (Control) | Retry-All ×3 (Naive) | Backstop (Agent) |
|---|---|---|---|
| Gross Recovered | ₹11,72,870.00 | ₹12,95,854.00 | **₹19,38,767.00** |
| **Incremental Lift (₹)** | ₹0.00 | ₹1,22,984.00 | **₹11,33,609.11** |
| **Lift (95% CI)** | Baseline | +1.7 pp | **+19.1% [+13.5%, +24.8%]** |
| Customer Contacts | 0 | 2,000 | **235 (88.2% reduction)** |
| Contacts / ₹1,000 Recovered | 0.00 | 1.54 | **0.12** |
| Policy Violations | 0 | 690 | **0 (Flawless)** |
| Hard Stops Auto-Actioned | 0 | 42 | **0 (Human Only)** |
