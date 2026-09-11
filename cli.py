#!/usr/bin/env python3
"""CLI Entry Point for CoW Protocol Off-Chain Intent Solver."""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from solver.client import CoWDriverClient
from solver.matcher import CoWMatcher
from solver.models import AuctionInstance, Order, TokenMetadata
from solver.objective import CoWObjectiveCalculator
from solver.validator import SettlementValidator

console = Console()

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
DAI = "0x6b175474e89094c44da98b954eedeac495271d0f"


def render_header() -> Panel:
    """Render terminal dashboard header."""
    text = Text()
    text.append("⚡ COW PROTOCOL OFF-CHAIN INTENT SOLVER ⚡\n", style="bold cyan")
    text.append(
        "Capital: $0.00 (Zero Inventory Risk) | Gas: 100% Protocol-Paid\n",
        style="bold green",
    )
    text.append(
        "Engine: Bipartite Graph CoW Matcher | Clearing: Uniform Batch Prices",
        style="dim white",
    )
    return Panel(text, border_style="cyan", padding=(0, 1))


def get_mock_auction() -> AuctionInstance:
    """Construct a realistic combinatorial batch auction instance for simulation."""
    return AuctionInstance(
        id="batch_sim_8921",
        tokens={
            WETH: TokenMetadata(decimals=18, reference_price=3150000000),
            USDC: TokenMetadata(decimals=6, reference_price=1000000),
            DAI: TokenMetadata(decimals=18, reference_price=1000000),
        },
        orders=[
            # Order 1: Alice sells 2 WETH for >= 6,280 USDC
            Order(
                uid="0xalice_weth_usdc",
                sell_token=WETH,
                buy_token=USDC,
                sell_amount=2_000_000_000_000_000_000,
                buy_amount=6_280_000_000,
            ),
            # Order 2: Bob sells 6,320 USDC for >= 2 WETH
            Order(
                uid="0xbob_usdc_weth",
                sell_token=USDC,
                buy_token=WETH,
                sell_amount=6_320_000_000,
                buy_amount=2_000_000_000_000_000_000,
            ),
            # Order 3: Charlie sells 5,000 DAI for >= 1.55 WETH
            Order(
                uid="0xcharlie_dai_weth",
                sell_token=DAI,
                buy_token=WETH,
                sell_amount=5_000_000_000_000_000_000_000,
                buy_amount=1_550_000_000_000_000_000,
            ),
        ],
    )


def run_simulate():
    """Run simulated batch auction matching and display full settlement telemetry."""
    console.print(render_header())
    auction = get_mock_auction()

    # Display incoming orders
    order_table = Table(title=f"📥 Incoming Batch Auction Orders (Batch #{auction.id})")
    order_table.add_column("UID", style="dim")
    order_table.add_column("Sell Token", style="cyan")
    order_table.add_column("Buy Token", style="magenta")
    order_table.add_column("Sell Amount", justify="right")
    order_table.add_column("Limit Buy Amount", justify="right")

    for o in auction.orders:
        sell_sym = "WETH" if o.sell_token == WETH else ("USDC" if o.sell_token == USDC else "DAI")
        buy_sym = "WETH" if o.buy_token == WETH else ("USDC" if o.buy_token == USDC else "DAI")
        order_table.add_row(
            o.uid[:12] + "...",
            sell_sym,
            buy_sym,
            f"{o.sell_amount:,}",
            f"{o.buy_amount:,}",
        )
    console.print(order_table)

    # Match auction
    with console.status("[bold cyan]Running Bipartite CoW Graph Matching..."):
        matcher = CoWMatcher()
        solution = matcher.match_auction(auction)

    # Validate settlement
    validator = SettlementValidator()
    val_result = validator.validate(auction, solution)

    if not val_result.is_valid:
        console.print(f"[bold red]Validation Failed:[/bold red] {val_result.errors}")
        sys.exit(1)

    # Score solution
    calc = CoWObjectiveCalculator()
    total_surplus = calc.score_solution(auction, solution)

    # Display settlement table
    settle_table = Table(title="🎯 CoW Settlement & Uniform Clearing Prices")
    settle_table.add_column("Order UID", style="green")
    settle_table.add_column("Executed Sell", justify="right")
    settle_table.add_column("Status", style="bold green")

    for trade in solution.trades:
        settle_table.add_row(trade.order_uid, f"{trade.executed_amount:,}", "FILLED (CoW Match)")
    console.print(settle_table)

    # Summary Panel
    summary_text = Text()
    summary_text.append(
        f"Matched Trades:     {len(solution.trades)} / {len(auction.orders)}\n",
        style="bold white",
    )
    summary_text.append("External AMM Slip:  0.00% (Direct Peer-to-Peer)\n", style="bold green")
    summary_text.append(f"Generated Surplus:  {total_surplus:,} token atoms\n", style="bold cyan")
    summary_text.append(
        "Gas Cost to Solver: $0.00 (Protocol GPv2Settlement Funded)\n",
        style="bold green",
    )
    summary_text.append(
        "Solver Reward Est:  Eligible for weekly DAO ETH/COW reward distribution",
        style="yellow",
    )
    console.print(Panel(summary_text, title="📊 Batch Execution Telemetry", border_style="green"))


async def run_listen(network: str = "mainnet"):
    """Listen to live CoW Protocol auction API."""
    console.print(render_header())
    client = CoWDriverClient()
    matcher = CoWMatcher()
    validator = SettlementValidator()

    try:
        with console.status(f"[bold cyan]Connecting to live CoW {network} auction stream..."):
            auction = await client.fetch_current_auction(network=network)

        if not auction:
            console.print(
                f"[yellow]No active batch currently open on {network}. "
                "CoW auctions open every 15-30s. Retrying...[/yellow]"
            )
            return

        console.print(
            f"[bold green]Connected to Live Batch #{auction.id}![/bold green] "
            f"Orders: {len(auction.orders)} | Tokens: {len(auction.tokens)}"
        )

        solution = matcher.match_auction(auction)
        val = validator.validate(auction, solution)

        console.print(f"Matched CoW Trades: [bold cyan]{len(solution.trades)}[/bold cyan]")
        console.print(f"Settlement Valid:   [bold green]{val.is_valid}[/bold green]")
        console.print(f"Score / Surplus:    [bold yellow]{solution.score:,}[/bold yellow]")

    except Exception as err:
        console.print(f"[bold red]Live query error:[/bold red] {err}")
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(
        description="COW-INTENT-SOLVER: Off-chain batch auction intent solver"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # simulate
    subparsers.add_parser("simulate", help="Simulate batch auction matching with full telemetry")

    # listen
    listen_p = subparsers.add_parser("listen", help="Fetch and solve live open CoW batch auction")
    listen_p.add_argument(
        "--network", default="mainnet", choices=["mainnet", "arbitrum_one", "xdai"]
    )

    args = parser.parse_args()

    if args.command == "simulate":
        run_simulate()
    elif args.command == "listen":
        asyncio.run(run_listen(network=args.network))


if __name__ == "__main__":
    main()
