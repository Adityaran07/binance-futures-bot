"""
Input validation for order parameters.
All validators raise ValueError with human-readable messages on failure.
"""

from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """Return upper-cased symbol or raise ValueError."""
    symbol = symbol.strip().upper()
    if not symbol or not symbol.isalpha():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphabetic (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return upper-cased side or raise ValueError."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(VALID_SIDES)}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return upper-cased order type or raise ValueError."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> str:
    """Return quantity as a string-formatted Decimal or raise ValueError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    return str(qty)


def validate_price(price: Optional[str | float], order_type: str) -> Optional[str]:
    """
    Validate price field.
    - MARKET orders: price must be None / not supplied.
    - LIMIT / STOP_MARKET orders: price must be a positive number.
    Returns the price as a string-formatted Decimal, or None for MARKET.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        if price is not None:
            raise ValueError("Price should not be supplied for MARKET orders.")
        return None

    # LIMIT and STOP_MARKET require a price
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")
    return str(p)


def validate_stop_price(
    stop_price: Optional[str | float], order_type: str
) -> Optional[str]:
    """
    Validate stop price (only relevant for STOP_MARKET).
    Returns the stop price as string or None.
    """
    if order_type.upper() != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("stopPrice is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'.")
    if sp <= 0:
        raise ValueError(f"Stop price must be positive, got {sp}.")
    return str(sp)
