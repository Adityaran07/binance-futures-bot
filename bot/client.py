"""
Low-level Binance Futures Testnet REST client.

Handles:
- HMAC-SHA256 request signing
- Timestamp injection
- HTTP error surfacing with structured logging
- Response parsing
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger(__name__)

BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance USDT-M Futures Testnet REST API.

    Args:
        api_key:    Your testnet API key.
        api_secret: Your testnet API secret.
        timeout:    HTTP timeout in seconds (default 10).
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised (base_url=%s)", BASE_URL)

    # ── Signing ───────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append timestamp + HMAC-SHA256 signature to params dict."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request, handle errors, and return the parsed JSON body.

        Args:
            method: HTTP method (GET / POST / DELETE).
            path:   API path (e.g. '/fapi/v1/order').
            params: Query / body parameters.
            signed: Whether to sign the request.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            BinanceAPIError: On API-level errors.
            requests.RequestException: On network-level failures.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = BASE_URL + path
        logger.debug("→ %s %s  params=%s", method.upper(), url, self._redact(params))

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() != "GET" else None,
                timeout=self._timeout,
            )
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.Timeout as exc:
            logger.error("Request timed out after %ss: %s", self._timeout, exc)
            raise

        logger.debug(
            "← HTTP %s  body=%s", response.status_code, response.text[:500]
        )

        data: Dict[str, Any] = {}
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (status %s): %s", response.status_code, response.text)
            response.raise_for_status()
            return {}

        if not response.ok or "code" in data and data["code"] < 0:
            code = data.get("code", response.status_code)
            msg = data.get("msg", response.text)
            logger.error("Binance API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    # ── Public endpoints ──────────────────────────────────────────────────────

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info (symbol rules, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict[str, Any]:
        """Fetch account balances and positions (requires signature)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    # ── Order endpoints ───────────────────────────────────────────────────────

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Place a new futures order.

        Keyword args are passed directly to POST /fapi/v1/order.
        Common keys: symbol, side, type, quantity, price, timeInForce, stopPrice.
        """
        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s",
            kwargs.get("symbol"),
            kwargs.get("side"),
            kwargs.get("type"),
            kwargs.get("quantity"),
            kwargs.get("price", "—"),
        )
        result = self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)
        logger.info(
            "Order accepted: orderId=%s status=%s executedQty=%s avgPrice=%s",
            result.get("orderId"),
            result.get("status"),
            result.get("executedQty"),
            result.get("avgPrice"),
        )
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling orderId=%s on %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of params with 'signature' replaced by '***'."""
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted
