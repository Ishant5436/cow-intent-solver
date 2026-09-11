# CoW Grants Program Application: Deterministic CoW Graph Matcher

## 1. Project Title
**Deterministic Bipartite Coincidence-of-Wants (CoW) Matcher & Invariant Validator**

## 2. Applicant Information
* **Applicant:** Ishant Panchal
* **GitHub:** [Ishant5436](https://github.com/Ishant5436)
* **Email:** ishant.p@somaiya.edu
* **Repository:** [https://github.com/Ishant5436/cow-intent-solver](https://github.com/Ishant5436/cow-intent-solver)

---

## 3. Executive Summary
This project delivers a high-performance, deterministic off-chain solver for CoW Protocol batch auctions. The solver discovers bilateral Coincidence-of-Wants (CoW) order crossings, derives uniform clearing prices with dynamic $10^{18}$ scaling across disparate decimal regimes, and validates settlements using independent authorized-inflow conservation guarantees ($\sum \text{Outflow} \le \sum \text{Authorized Inflow}$).

By prioritizing pure peer-to-peer internal order crossing, the solver completely eliminates external Automated Market Maker (AMM) slippage, reduces LVR (Loss-Versus-Rebalancing), and creates maximal trader surplus.

---

## 4. Problem & Solution

### The Challenge
External liquidity routing (e.g. via Uniswap v3 or Curve) exposes batch settlements to exchange fees, liquidity fragmentation, and adverse selection. In high-volume pairs, counter-directional retail orders frequently overlap in limit prices but fail to match if solvers default to standard DEX routing heuristics.

### The Solution
A dedicated graph-based bipartite matching engine that:
1. **Identifies Bilateral Crossings:** Matches counter-directional limit orders ($A \rightarrow B$ and $B \rightarrow A$).
2. **Computes Uniform Clearing Prices:** Derives equilibrium prices with dynamic $10^{18}$ scaling to eliminate integer truncation when trading small-unit pairs (e.g. WETH vs USDC).
3. **Guarantees Safety Invariants:**
   * Limit price enforcement against signed order ratios.
   * Matched order UID deduplication preventing double-fills.
   * Transitive price boundary guards preventing stale-price execution across multi-pair chains.
   * Independent token conservation: Inflow is strictly bounded by user-signed allowances ($\min(\text{sell\_amount}, \text{executed})$).

---

## 5. Technical Specifications & Verified Deliverables

* **Language & Runtime:** Python 3.12 (modular, memory-safe, zero custom wrappers).
* **Test Coverage:** 19/19 unit and regression tests passing in 0.10s.
* **Live Connectivity:** Verified real-time connection to CoW Protocol staging auction batches (`https://barn.api.cow.fi/mainnet/api/v1/auction`).
* **Telemetry CLI:** Full terminal dashboard (`simulate` and `listen`) displaying batch order books, matched settlements, generated surplus, and validation results.

---

## 6. Milestones & Budget Request ($20,000 USD / COW)

### Milestone 1: Core Bipartite Matching Engine & Invariant Validator ($8,000) — [COMPLETED]
* Working open-source solver repository with full test suite.
* Pydantic v2 data models for `AuctionInstance`, `Order`, `Solution`.
* Deterministic bilateral CoW matching engine with dynamic scaling.
* Independent `SettlementValidator` with non-tautological conservation and limit verification.
* CLI with simulation and live batch polling.

### Milestone 2: Multi-Hop Cyclic CoW Matching ($7,000) — [4 Weeks]
* Extend matcher from bilateral pairs to $N$-token cycles ($A \rightarrow B \rightarrow C \rightarrow A$) using Bellman-Ford negative-log exchange rate cycle detection.
* Solve combinatorial triangular arbitrage internally without external liquidity.
* Full unit test suite and invariant validation for cyclic settlements.

### Milestone 3: Driver Integration & Shadow Benchmarking ($5,000) — [3 Weeks]
* Package solver with standard CoW driver HTTP interface (`/solve`).
* Run shadow evaluation alongside production batches on Ethereum Mainnet and Gnosis Chain.
* Publish open benchmark report measuring generated surplus, gas reduction, and CoW percentage.

---

## 7. Open-Source Commitment
All code is and will remain strictly open-source under the MIT license, accessible to the entire CoW DAO ecosystem.
