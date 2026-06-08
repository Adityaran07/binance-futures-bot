# Binance Futures Testnet — Trading Bot

A clean, production-structured Python CLI for placing orders on the **Binance USDT-M Futures Testnet**.  
Supports **MARKET**, **LIMIT**, and **STOP_MARKET** order types with full validation, structured logging, and detailed error handling.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Low-level Binance REST client (signing, HTTP, error parsing)
│   ├── orders.py          # Order placement logic + OrderResult dataclass
│   ├── validators.py      # Input validation (symbol, side, type, qty, price)
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log    # Rotates at 5 MB, keeps 3 backups
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Get Testnet API Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account.
3. Click **API Key** (top right) → copy your **API Key** and **Secret Key**.

### 2. Clone & Install

```bash
git clone <your-repo-url>
cd trading_bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set Credentials

**Option A — Environment variables (recommended):**

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

**Option B — CLI flags** (less secure, appear in shell history):

```bash
python cli.py --api-key <KEY> --api-secret <SECRET> ...
```

---

## Usage

### General syntax

```
python cli.py --symbol SYMBOL --side BUY|SELL --type MARKET|LIMIT|STOP_MARKET \
              --quantity QTY [--price PRICE] [--stop-price STOP_PRICE] [--tif GTC|IOC|FOK]
```

### Interactive Mode (Bonus — Enhanced CLI UX)

Run a guided interactive session with menus, prompts, and inline validation:

```bash
python interactive.py
```

No flags needed — it walks you through everything step by step:
- Loads credentials from environment variables automatically
- Numbered menus for Side and Order Type
- Inline validation with clear error messages on bad input
- Confirmation prompt before placing any order
- Colour-coded output (green for BUY, red for SELL)

---

### Run in Mock Mode (no testnet account needed)

If the testnet is inaccessible (e.g. regional restrictions in India), use `--mock` flag:

```bash
# Mock MARKET order
python cli.py --mock --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Mock LIMIT order
python cli.py --mock --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Mock STOP_MARKET order
python cli.py --mock --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 3200
```

Mock mode simulates real Binance API responses (same schema, realistic prices, order IDs) without making any network calls. All validation, logging, and error handling remain identical to live mode.

---

### Place a MARKET order

```bash
# Buy 0.001 BTC at market price
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Sell 0.01 ETH at market price
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a LIMIT order

```bash
# Sell 0.001 BTC at $70,000 (Good-Till-Cancelled)
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Buy 0.01 ETH at $3,100, Fill-Or-Kill
python cli.py --symbol ETHUSDT --side BUY --type LIMIT --quantity 0.01 --price 3100 --tif FOK
```

### Place a STOP_MARKET order *(bonus)*

```bash
# Trigger a market BUY when ETHUSDT hits $3,200
python cli.py --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 3200
```

### Increase log verbosity

```bash
python cli.py --log-level DEBUG --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Sample Output

```
  Order Request Summary
  ──────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001

┌─────────────────────────────────────────┐
│           ORDER CONFIRMATION            │
├─────────────────────────────────────────┤
│  Order ID      : 4294937639             │
│  Symbol        : BTCUSDT               │
│  Side          : BUY                   │
│  Type          : MARKET                │
│  Quantity      : 0.001                 │
│  Price         : 0                     │
│  Executed Qty  : 0.001                 │
│  Avg Price     : 67482.10000           │
│  Status        : FILLED                │
│  Time-in-Force : GTC                   │
└─────────────────────────────────────────┘

  ✓ Order placed successfully!
```

---

## Logging

- **Console**: INFO-level and above (human-readable timestamps).
- **File**: DEBUG-level and above → `logs/trading_bot.log` (rotates at 5 MB, 3 backups kept).
- Secrets (`signature`) are always redacted before logging.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API credentials | Prints usage hint and exits with code 1 |
| Invalid symbol / side / type | Validation error with clear message |
| Price missing for LIMIT order | Validation error before any network call |
| Binance API error (e.g. `-2021`) | Error code + message logged and printed |
| Network timeout / connection failure | Exception logged; non-zero exit |

---

## Assumptions

- Targeting **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`).
- Quantity precision is passed as-is; if Binance rejects with `-1111` (precision error), adjust your `--quantity` to match the symbol's `stepSize` filter.
- `STOP_MARKET` stop price must be outside the current market price direction (Binance enforces this; otherwise you'll get `-2021`).
- No position-mode setting is performed; the account is assumed to be in **One-way** mode (default on the testnet).

---

## Requirements

```
requests>=2.31.0
```

Python 3.8+ required.
