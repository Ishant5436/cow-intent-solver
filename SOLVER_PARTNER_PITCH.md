# Solver Consortium Technical Brief: Pure CoW Bipartite Matching Heuristic

**Target Audience:** Bonded CoW Protocol Solvers (Barter, Maven11, Launchnodes, Baseline, etc.)  
**Repository:** [https://github.com/Ishant5436/cow-intent-solver](https://github.com/Ishant5436/cow-intent-solver)  
**Author:** Ishant Panchal (ishant.p@somaiya.edu)

---

## 1. Proposal: Plug-in CoW Matching for Existing Solver Infrastructure

As an established bonded solver, your primary objective in every batch auction is maximizing objective score:
$$\text{Score} = \text{Surplus} - \text{Gas Cost} - \text{Execution Risk}$$

Most production solvers focus heavily on AMM pathfinding (Uniswap v3 pools, Curve, Balancer) and private order flow. However, routing through AMMs incurs:
1. Pool swap fees (0.01% - 0.30% per hop).
2. Price impact / slippage.
3. On-chain execution gas fees.

### The Opportunity: Zero-Gas, Zero-Slippage Internal CoWs
We have built and verified an off-chain graph-based bipartite CoW matching engine designed to run as a **pre-pass filter** before AMM routing:
1. **Extracts Direct CoWs:** Identifies all counter-directional orders with overlapping limit spreads and executes them at uniform clearing prices.
2. **Eliminates AMM Slippage:** Direct peer-to-peer fills generate 100% pure surplus with zero external market friction.
3. **Residual AMM Routing:** The remaining unmatched volume is passed to your existing AMM route optimizer.

---

## 2. Technical Architecture & Safety Guarantees

* **Deterministic Precision:** Uniform clearing prices computed with dynamic $10^{18}$ scale factors, eliminating integer truncation across disparate decimal regimes (e.g. WETH 18 decimals vs USDC 6 decimals).
* **Order Deduplication:** Strict UID deduplication preventing double-fill vulnerabilities.
* **Transitive Price Consistency:** In multi-token chains ($A/B$, $B/C$, $A/C$), transitive prices are validated against current limit bounds before emitting settlement trades.
* **Independent Conservation Validator:** Validates that total token outflow never exceeds authorized signed inflow ($\sum \text{Outflow} \le \sum \text{Authorized Inflow}$), ensuring settlements never revert on-chain.
* **Tested & Benchmarked:** 19/19 passing unit tests in 0.10s, verified live against CoW Protocol staging batches (`https://barn.api.cow.fi`).

---

## 3. Partnership & Integration Model

* **Effortless Integration:** Modular Python / C++ service that consumes batch auction JSON and returns candidate settlements:
  ```python
  solution = matcher.match_auction(auction_instance)
  ```
* **Commercial Model:**
  * **Profit Share:** 30% to 50% split of weekly CoW DAO solver rewards on batches won via this CoW matching heuristic.
  * **Zero Upfront Cost:** No licensing fees. 100% performance-aligned.
