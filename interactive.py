#!/usr/bin/env python3
"""
interactive.py — Enhanced interactive CLI for the Binance Futures Trading Bot.

Bonus feature: Enhanced CLI UX with menus, prompts, and inline validation.

Run with:
  python interactive.py
"""

from __future__ import annotations

import os
import sys

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import get_logger, setup_logging
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

setup_logging(level="INFO")
logger = get_logger(__name__)

# ── Colours (Windows-safe fallback) ──────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# ── UI helpers ────────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print(f"{CYAN}{BOLD}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║    Binance Futures  ·  Interactive Bot       ║")
    print("  ║    USDT-M  ·  Demo / Testnet Environment    ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"{RESET}")

def section(title: str):
    print(f"\n{CYAN}  ── {title} {'─' * (38 - len(title))}{RESET}")

def ok(msg: str):
    print(f"  {GREEN}✓{RESET}  {msg}")

def err(msg: str):
    print(f"  {RED}✗  {msg}{RESET}")

def warn(msg: str):
    print(f"  {YELLOW}⚠  {msg}{RESET}")

def prompt(label: str, hint: str = "") -> str:
    hint_str = f"{DIM}  ({hint}){RESET}" if hint else ""
    return input(f"  {BOLD}{label}{RESET}{hint_str}: ").strip()

def choose(label: str, options: list[str]) -> str:
    """Display numbered menu, return chosen value."""
    print(f"\n  {BOLD}{label}{RESET}")
    for i, opt in enumerate(options, 1):
        print(f"    {CYAN}[{i}]{RESET}  {opt}")
    while True:
        raw = input(f"  Enter choice (1-{len(options)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            chosen = options[int(raw) - 1]
            ok(f"Selected: {BOLD}{chosen}{RESET}")
            return chosen
        err(f"Please enter a number between 1 and {len(options)}.")

def confirm(msg: str) -> bool:
    ans = input(f"\n  {YELLOW}{msg} [y/N]{RESET}: ").strip().lower()
    return ans == "y"


# ── Validated prompt helpers ──────────────────────────────────────────────────

def ask_symbol() -> str:
    while True:
        raw = prompt("Trading Symbol", "e.g. BTCUSDT, ETHUSDT")
        try:
            val = validate_symbol(raw)
            ok(f"Symbol accepted: {BOLD}{val}{RESET}")
            return val
        except ValueError as e:
            err(str(e))

def ask_quantity() -> str:
    while True:
        raw = prompt("Quantity", "base asset amount, e.g. 0.001")
        try:
            val = validate_quantity(raw)
            ok(f"Quantity accepted: {BOLD}{val}{RESET}")
            return val
        except ValueError as e:
            err(str(e))

def ask_price(order_type: str) -> str | None:
    if order_type == "MARKET":
        return None
    while True:
        raw = prompt("Limit Price", "e.g. 70000")
        try:
            val = validate_price(raw, order_type)
            ok(f"Price accepted: {BOLD}{val}{RESET}")
            return val
        except ValueError as e:
            err(str(e))


# ── Credential setup ──────────────────────────────────────────────────────────

def get_credentials() -> tuple[str, str]:
    api_key    = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")

    if api_key and api_secret:
        ok("Credentials loaded from environment variables.")
        return api_key, api_secret

    warn("No credentials found in environment variables.")
    section("API Credentials")
    print(f"  {DIM}Keys are used only for this session and never stored.{RESET}\n")
    api_key    = prompt("API Key")
    api_secret = prompt("API Secret")

    if not api_key or not api_secret:
        err("Credentials cannot be empty. Exiting.")
        sys.exit(1)

    ok("Credentials accepted.")
    return api_key, api_secret


# ── Order summary ─────────────────────────────────────────────────────────────

def print_order_summary(symbol, side, order_type, quantity, price=None):
    section("Order Summary")
    print(f"  {'Symbol':<14}: {BOLD}{symbol}{RESET}")
    print(f"  {'Side':<14}: {BOLD}{GREEN if side=='BUY' else RED}{side}{RESET}")
    print(f"  {'Order Type':<14}: {BOLD}{order_type}{RESET}")
    print(f"  {'Quantity':<14}: {BOLD}{quantity}{RESET}")
    if price:
        print(f"  {'Limit Price':<14}: {BOLD}{price}{RESET}")


# ── Main interactive flow ─────────────────────────────────────────────────────

def main():
    clear()
    banner()

    # Credentials
    section("Credentials")
    api_key, api_secret = get_credentials()

    while True:
        # ── Main menu ─────────────────────────────────────────────────────────
        section("Main Menu")
        action = choose("What would you like to do?", [
            "Place a new order",
            "Exit",
        ])

        if action == "Exit":
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            break

        # ── Order flow ────────────────────────────────────────────────────────
        section("Order Setup")

        symbol     = ask_symbol()
        side       = choose("Order Side", ["BUY", "SELL"])
        order_type = choose("Order Type", ["MARKET", "LIMIT"])
        quantity   = ask_quantity()
        price      = ask_price(order_type)

        if order_type == "LIMIT":
            tif = choose("Time-in-Force", ["GTC", "IOC", "FOK"])
        else:
            tif = "GTC"

        # Confirm before sending
        print_order_summary(symbol, side, order_type, quantity, price)

        if not confirm("Confirm and place this order?"):
            warn("Order cancelled.")
            continue

        # ── Place order ───────────────────────────────────────────────────────
        section("Placing Order")
        client  = BinanceClient(api_key=api_key, api_secret=api_secret)
        manager = OrderManager(client)

        try:
            if order_type == "MARKET":
                result = manager.place_market_order(symbol=symbol, side=side, quantity=quantity)
            else:
                result = manager.place_limit_order(
                    symbol=symbol, side=side, quantity=quantity,
                    price=price, time_in_force=tif,
                )

            print(f"\n{result.summary()}")
            ok(f"Order placed! {BOLD}orderId={result.order_id}{RESET}  status={result.status}")
            logger.info("Interactive order placed. orderId=%s status=%s", result.order_id, result.status)

        except BinanceAPIError as e:
            err(f"Binance rejected the order — code {e.code}: {e.message}")
            logger.error("BinanceAPIError %s: %s", e.code, e.message)
        except Exception as e:
            err(f"Unexpected error: {e}")
            logger.error("Unexpected error: %s", e)

        if not confirm("Place another order?"):
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            break


if __name__ == "__main__":
    main()
