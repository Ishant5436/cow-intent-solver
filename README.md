# cow-intent-solver

High-Performance CoW Protocol Off-Chain Intent Solver and Batch Auction Matching Engine.

## Highlights
- **Strictly $0.00 Capital Requirement:** Solvers never execute transactions or hold inventory; the CoW Protocol `GPv2Settlement` contract executes winning solutions and pays 100% of on-chain gas.
- **Coincidence-of-Wants (CoW) Engine:** Bipartite graph order crossing that matches counter-directional trades internally at uniform clearing prices, eliminating AMM slippage and LP fees.
- **Surplus Maximization:** Ranks and scores solutions to optimize trader utility and maximize protocol solver rewards.
- **Deterministic Invariant Validation:** Validates limit prices, balance conservation, and uniform clearing prices before solution submission.

## Quick Start

### 1. Environment Setup
```bash
cd /Users/ishantpanchal/cow-intent-solver
source .venv/bin/activate
```

### 2. Run Offline Batch Auction Simulation
Simulate a multi-token combinatorial auction and observe CoW matching, clearing prices, and surplus calculation:
```bash
python cli.py simulate
```

### 3. Connect to Live CoW Protocol Auction Stream
Query live open batch auctions from CoW Protocol and run real-time matching:
```bash
python cli.py listen --network mainnet
```

### 4. Run Verification Tests
```bash
pytest tests/ -v
ruff check .
```
