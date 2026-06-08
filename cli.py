#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet trading bot.

Usage examples:
  # Market BUY
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

  # Stop-Market BUY (bonus)
  python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 60000

  # Override credentials inline
  python cli.py --api-key <KEY> --api-secret <SECRET> --symbol ETHUSDT --side BUY --type MARKET --quantity 0.01

Environment variables (preferred over flags for secrets):
  BINANCE_API_KEY
  BINANCE_API_SECRET
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import get_logger, setup_logging
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

# ── Initialise logging before any other imports use it ────────────────────────
setup_logging(level="INFO")
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Argument Parser
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            ╔══════════════════════════════════════════╗
            ║   Binance Futures Testnet  Trading Bot   ║
            ╚══════════════════════════════════════════╝

            Place MARKET, LIMIT, or STOP_MARKET orders on the
            Binance USDT-M Futures Testnet.
            """
        ),
        epilog=textwrap.dedent(
            """\
            Examples:
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
              python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000
              python cli.py --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 3000
            """
        ),
    )

    # Credentials
    creds = parser.add_argument_group("credentials (env vars preferred)")
    creds.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY"),
        metavar="KEY",
        help="Binance Testnet API key (or set BINANCE_API_KEY env var).",
    )
    creds.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET"),
        metavar="SECRET",
        help="Binance Testnet API secret (or set BINANCE_API_SECRET env var).",
    )

    # Order parameters
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT.",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        metavar="SIDE",
        help="Order side: BUY or SELL.",
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        metavar="TYPE",
        help="Order type: MARKET | LIMIT | STOP_MARKET.",
    )
    order.add_argument(
        "--quantity",
        required=True,
        metavar="QTY",
        help="Order quantity (base asset, e.g. 0.001 BTC).",
    )
    order.add_argument(
        "--price",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders).",
    )
    order.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_MARKET orders).",
    )
    order.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        metavar="TIF",
        help="Time-in-force for LIMIT orders (default: GTC).",
    )

    # Misc
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO).",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_request_summary(args: argparse.Namespace) -> None:
    print()
    print("  Order Request Summary")
    print("  " + "─" * 38)
    print(f"  Symbol     : {args.symbol.upper()}")
    print(f"  Side       : {args.side.upper()}")
    print(f"  Type       : {args.order_type.upper()}")
    print(f"  Quantity   : {args.quantity}")
    if args.price:
        print(f"  Price      : {args.price}")
    if args.stop_price:
        print(f"  Stop Price : {args.stop_price}")
    print()


def _abort(message: str) -> None:
    logger.error(message)
    print(f"\n  ✗ ERROR: {message}\n", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Re-apply log level if user changed it
    setup_logging(level=args.log_level)

    # ── Credential check ──────────────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        _abort(
            "API credentials missing. "
            "Set BINANCE_API_KEY / BINANCE_API_SECRET env vars, "
            "or pass --api-key / --api-secret."
        )

    # ── Input validation ──────────────────────────────────────────────────────
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity = validate_quantity(args.quantity)

        if order_type == "LIMIT":
            validate_price(args.price, order_type)
        elif order_type == "STOP_MARKET":
            validate_stop_price(args.stop_price, order_type)

    except ValueError as exc:
        _abort(str(exc))

    # ── Print summary before sending ──────────────────────────────────────────
    _print_request_summary(args)
    logger.info(
        "Request: symbol=%s side=%s type=%s qty=%s",
        symbol, side, order_type, quantity,
    )

    # ── Initialise client + manager ───────────────────────────────────────────
    client = BinanceClient(api_key=args.api_key, api_secret=args.api_secret)
    manager = OrderManager(client)

    # ── Dispatch to correct order type ────────────────────────────────────────
    try:
        if order_type == "MARKET":
            result = manager.place_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
            )
        elif order_type == "LIMIT":
            result = manager.place_limit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=args.price,
                time_in_force=args.tif,
            )
        else:  # STOP_MARKET
            result = manager.place_stop_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=args.stop_price,
            )

    except BinanceAPIError as exc:
        _abort(f"Binance API rejected the order — code {exc.code}: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        _abort(f"Unexpected error: {exc}")

    # ── Success output ────────────────────────────────────────────────────────
    print(result.summary())
    print(f"\n  ✓ Order placed successfully!\n")
    logger.info("Order placed successfully. orderId=%s", result.order_id)


if __name__ == "__main__":
    main()
