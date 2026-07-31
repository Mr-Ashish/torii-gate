# Hub71 full rescore — all collated ideas (2026-08-01)

**N = 25 ideas** · Dimensions: A1–A5, B1–B6, C1–C6, D1, E1/E2/E4, F1–F3 (23 atomic)  
**Weights:** PMF 30% · UAE 19% · doors 16% · ship 12% · asset 13% · legal 10%  
**Rules:** MZN = OUT for all · Build list requires D1 ≥ 4  
**CSV:** `idea-scores-hub71-all.csv`

## Ranked table

| Rk | ID | Final | Gr | PMF | Hub | Ship | Legal | Build | Idea |
|---:|----|------:|:--:|----:|----:|-----:|------:|:-----:|------|
| 1 | **C1** | **4.65** | A | 5.00 | 3.92 | 5.00 | 5.00 | YES | Torii Gate PR/CI security gate |
| 2 | **LUFFY_PLAT** | **4.55** | A | 4.80 | 4.00 | 4.20 | 5.00 | YES | Platform pitch C1+C2→C4 (apply narrative) |
| 3 | **C2** | **4.40** | A | 4.60 | 3.92 | 4.00 | 5.00 | YES | Hybrid SAST→agent validator |
| 4 | W2 | 4.25 | B | 4.80 | 3.58 | 5.00 | 5.00 | YES | Commerce integration reliability |
| 5 | **C4** | **4.20** | B | 4.40 | 3.75 | 3.80 | 4.33 | YES | Torii Plane — agentic coding security control plane |
| 6 | W1 | 4.17 | B | 4.80 | 3.58 | 4.20 | 4.33 | YES | General agent control plane |
| 7 | W4 | 4.06 | B | 4.60 | 3.17 | 5.00 | 5.00 | YES | Support-agent eval suite |
| 8 | C6 | 3.86 | C | 4.00 | 3.33 | 4.00 | 5.00 | YES | IaC / cloud policy agent |
| 9 | C5 | 3.85 | C | 4.60 | 2.92 | 4.40 | 5.00 | YES | Secrets + supply-chain PR |
| 10 | AGENT_GOV | 3.82 | C | 4.20 | 3.67 | 3.00 | 3.33 | NO | Enterprise agent fleet governance |
| 11 | C3 | 3.73 | C | 3.80 | 3.33 | 3.00 | 4.33 | NO | Repo autonomous security audit |
| 12 | W3 | 3.70 | C | 4.60 | 3.08 | 5.00 | 3.67 | YES | B2B collections agent |
| 13 | GEN_PR | 3.62 | C | 4.00 | 2.58 | 4.80 | 5.00 | YES | Generic AI PR review (CodeRabbit-like) |
| 14 | I6 | 3.33 | D | 3.60 | 3.75 | 3.00 | 2.67 | NO | India–GCC trade docs + WC AI |
| 15 | C9b | 3.27 | D | 3.80 | 3.33 | 2.40 | 2.67 | NO | Continuous AI pentest (phase-2) |
| 16 | API_AGENT | 3.21 | D | 3.20 | 2.67 | 3.80 | 4.67 | YES | Self-maintaining API agent (shell name) |
| 17 | C7 | 3.16 | D | 3.20 | 2.83 | 2.20 | 4.00 | NO | Auto-patch agent |
| 18 | S5 | 3.15 | D | 3.20 | 3.50 | 2.00 | 4.00 | NO | DC cooling/water optimizer |
| 19 | ASPM_L | 3.10 | D | 3.40 | 2.83 | 2.40 | 5.00 | NO | ASPM aggregation lite |
| 20 | LLM_RT | 3.01 | D | 3.40 | 3.00 | 2.40 | 2.67 | NO | LLM red-team as a service |
| 21 | SEC1_CLONE | 3.01 | D | 3.20 | 3.25 | 2.00 | 2.67 | NO | Full Sec1-style platform day-1 |
| 22 | S4 | 2.95 | F | 3.20 | 4.17 | 1.40 | 1.33 | NO | AI radiology (**prestige trap**) |
| 23 | DA | 2.69 | F | 3.20 | 3.58 | 1.40 | 1.67 | NO | RWA / tokenized finance |
| 24 | GEN | 2.65 | F | 2.40 | 2.08 | 3.40 | 4.67 | YES* | Generic multi-agent platform |
| 25 | SAVI | 2.56 | F | 2.40 | 3.33 | 1.20 | 3.00 | NO | Smart mobility / fleet twin |

\*GEN passes D1≥4 but final kills it — do not build.

## Decision for Hub71

| Role | ID | Why |
|------|-----|-----|
| **Apply product name** | LUFFY_PLAT / Torii | Best story score; contains C1→C2→C4 |
| **Build first** | C1 | Highest final + perfect ship + legal |
| **Build second** | C2 | Trust wedge / white space |
| **Roadmap vision** | C4 | +AI sovereign narrative |
| **Backup non-cyber** | W2 | Strong PMF+ship if pivot |
| **Do not apply as** | GEN_PR, SEC1_CLONE, S4, GEN | Red ocean / legal / prestige |

## Grade bands

- **A (≥4.3):** C1, LUFFY_PLAT, C2  
- **B (4.0–4.29):** W2, C4, W1, W4  
- **C (3.5–3.99):** C6, C5, AGENT_GOV, C3, W3, GEN_PR  
- **D/F:** everything else — deprioritize for Access
