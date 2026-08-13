"""CryptoForecast live market terminal and 30-day scenario dashboard."""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(
    page_title="CryptoForecast | Live Terminal",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
FORECAST_FRESHNESS_DAYS = 3
BINANCE_MARKET_BASE = "https://data-api.binance.vision"
REQUIRED_FILES = {
    "daily": "crypto_daily_final.csv",
    "future": "future_forecasts_all_models.csv",
    "comparison": "model_comparison_daily.csv",
    "status": "processing_status_all_71_coins.csv",
    "summary": "forecast_engine_run_summary.json",
}
LIVE_COLUMNS = [
    "symbol", "pair", "live_price", "change_24h", "high_24h", "low_24h",
    "quote_volume", "live_updated_at",
]

WHITE_THEME = {
    "background": "#f7f9fc",
    "surface": "#ffffff",
    "accent": "#00a57a",
    "secondary": "#4f647a",
}
ACCENT_COLOR = WHITE_THEME["accent"]
SECONDARY_COLOR = WHITE_THEME["secondary"]
POSITIVE_COLOR = "#007f5f"
NEGATIVE_COLOR = "#c92f48"
CHART_BG = "#ffffff"
CHART_FONT = "#405166"
CHART_TITLE = "#111827"
CHART_GRID = "#e6eaf0"
CHART_HOVER_BG = "#ffffff"
CHART_HOVER_FONT = "#111827"

CSS = """
<style>
    #MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    :root {
        --night:#030711; --panel:rgba(8,18,34,.86); --line:rgba(86,215,255,.16);
        --ink:#edf7ff; --muted:#88a0b8; --cyan:#43d9ff; --green:#28e0a0;
        --red:#ff5577; --amber:#ffc857; --violet:#8b7cff;
    }
    .stApp {
        color:var(--ink);
        background:
          linear-gradient(rgba(67,217,255,.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(67,217,255,.025) 1px, transparent 1px),
          radial-gradient(circle at 14% 6%, rgba(0,184,255,.15), transparent 28%),
          radial-gradient(circle at 92% 2%, rgba(139,124,255,.14), transparent 25%),
          linear-gradient(145deg,#02050c,#06101f 55%,#030711);
        background-size:34px 34px,34px 34px,auto,auto,auto;
    }
    [data-testid="stSidebar"] {
        background:linear-gradient(180deg,rgba(2,7,16,.99),rgba(5,15,29,.98));
        border-right:1px solid var(--line);
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color:#bdd0e2; }
    .block-container { max-width:1600px; padding-top:1rem; padding-bottom:2.5rem; }
    h1,h2,h3 { color:#f4fbff; letter-spacing:-.03em; }
    div[data-testid="stPlotlyChart"] {
        background:linear-gradient(145deg,rgba(5,14,27,.76),rgba(4,10,20,.58));
        border:1px solid var(--line); border-radius:18px; overflow:hidden;
        box-shadow:0 18px 55px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.03);
    }
    .brand { padding:.2rem 0 1rem; }
    .brand-name { font-weight:850; font-size:1.35rem; color:#f4fbff; }
    .brand-name span { color:var(--cyan); text-shadow:0 0 18px rgba(67,217,255,.65); }
    .brand-sub { color:#66839d; font-size:.68rem; letter-spacing:.16em; margin-top:.25rem; }
    .terminal-head {
        position:relative; overflow:hidden; padding:1.15rem 1.35rem; margin-bottom:.85rem;
        border:1px solid var(--line); border-radius:18px;
        background:linear-gradient(105deg,rgba(6,25,45,.96),rgba(15,14,44,.84));
        box-shadow:0 16px 45px rgba(0,0,0,.25);
    }
    .terminal-head:after {
        content:""; position:absolute; left:-30%; right:-30%; top:0; height:1px;
        background:linear-gradient(90deg,transparent,var(--cyan),transparent);
        animation:sweep 5s linear infinite;
    }
    .terminal-title { font-size:clamp(1.55rem,3vw,2.45rem); font-weight:850; line-height:1; }
    .terminal-sub { color:#8da6bd; margin-top:.38rem; font-size:.84rem; }
    .live-line { color:#7cebc2; font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; }
    .live-dot { display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);margin-right:7px;box-shadow:0 0 13px var(--green);animation:pulse 1.55s ease-in-out infinite; }
    .metric-grid { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:.7rem 0 1rem; }
    .metric {
        min-height:102px;padding:.85rem 1rem;border-radius:15px;border:1px solid var(--line);
        background:linear-gradient(145deg,rgba(9,25,45,.9),rgba(5,14,27,.92));
        box-shadow:inset 0 1px rgba(255,255,255,.035),0 10px 28px rgba(0,0,0,.2);
    }
    .metric-label { color:#7f98af;font-size:.67rem;letter-spacing:.12em;text-transform:uppercase;font-weight:750; }
    .metric-value { color:#f4fbff;font-size:1.55rem;font-weight:850;margin-top:.35rem;white-space:normal; }
    .metric-note { color:#718ba2;font-size:.72rem;margin-top:.2rem; }
    .up { color:var(--green)!important; } .down { color:var(--red)!important; } .warn { color:var(--amber)!important; }
    .ticker-shell { overflow:hidden;white-space:nowrap;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:.52rem 0;margin-bottom:.85rem;background:rgba(3,9,18,.62); }
    .ticker-track { display:inline-block;padding-left:100%;animation:ticker 40s linear infinite; }
    .ticker-item { margin-right:2.2rem;color:#a9bfd2;font-size:.82rem; }
    .signal-core {
        position:relative;min-height:270px;display:flex;align-items:center;justify-content:center;text-align:center;
        overflow:hidden;border-radius:26px;border:1px solid rgba(67,217,255,.24);
        background:radial-gradient(circle,rgba(67,217,255,.16),rgba(4,11,22,.96) 64%);
        box-shadow:inset 0 0 70px rgba(67,217,255,.07),0 22px 58px rgba(0,0,0,.34);
    }
    .signal-core:before,.signal-core:after { content:"";position:absolute;border-radius:50%; }
    .signal-core:before { width:205px;height:205px;border:1px dashed rgba(67,217,255,.46);animation:orbit 15s linear infinite; }
    .signal-core:after { width:155px;height:155px;border:2px solid rgba(139,124,255,.34);border-left-color:transparent;animation:orbit 8s linear infinite reverse; }
    .signal-content { z-index:2; }
    .signal-kicker { color:#75dfff;font-size:.67rem;letter-spacing:.17em;text-transform:uppercase; }
    .signal-action { font-size:clamp(2rem,5vw,3.35rem);font-weight:900;text-shadow:0 0 28px currentColor;margin:.25rem 0; }
    .signal-score { color:#8fa8be;font-size:.78rem; }
    .status-ribbon { display:flex;gap:.55rem;flex-wrap:wrap;margin:.5rem 0 .9rem; }
    .pill { padding:.3rem .64rem;border:1px solid var(--line);border-radius:999px;background:rgba(8,22,39,.8);font-size:.69rem;letter-spacing:.06em;color:#a9bfd2; }
    .pill-live { border-color:rgba(40,224,160,.3);color:#6fe8ba; }
    .pill-model { border-color:rgba(139,124,255,.32);color:#b5abff; }
    .trade-ticket { padding:1rem;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(8,23,41,.94),rgba(4,12,23,.94)); }
    .ticket-head { color:#78dcff;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.7rem; }
    .ticket-result { font-size:1.55rem;font-weight:850;color:#f4fbff;margin:.25rem 0; }
    .micro-grid { display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin:.7rem 0; }
    .micro { border-left:2px solid rgba(67,217,255,.55);padding:.4rem .65rem;background:rgba(8,22,39,.48); }
    .micro-label { color:#7290a8;font-size:.65rem;text-transform:uppercase;letter-spacing:.09em; }
    .micro-value { color:#eaf7ff;font-weight:800;margin-top:.16rem; }
    .radar-card { padding:.75rem .9rem;border-left:3px solid var(--cyan);background:rgba(8,22,39,.66);margin:.45rem 0;border-radius:0 12px 12px 0; }
    .easy-call { padding:1rem;border:1px solid var(--line);border-radius:16px;background:rgba(7,20,37,.82);min-height:110px; }
    .easy-label { color:#7b98b0;font-size:.68rem;text-transform:uppercase;letter-spacing:.1em; }
    .easy-value { color:#f3fbff;font-size:1.5rem;font-weight:850;margin:.3rem 0; }
    .fine-print { color:#5f788e;font-size:.68rem;text-align:center;padding-top:1rem; }
    @keyframes pulse { 0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.65);opacity:.5} }
    @keyframes orbit { to{transform:rotate(360deg)} }
    @keyframes sweep { from{transform:translateX(-25%)}to{transform:translateX(125%)} }
    @keyframes ticker { from{transform:translateX(0)}to{transform:translateX(-100%)} }
    @media (max-width:900px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.micro-grid{grid-template-columns:1fr}}
    @media (max-width:520px){.metric-grid{grid-template-columns:1fr}.block-container{padding-left:.65rem;padding-right:.65rem}.terminal-head{padding:1rem}.metric-value{font-size:1.35rem}}
    @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def locate_data_directory() -> Path:
    configured = os.getenv("CRYPTO_FORECAST_DATA_DIR", "").strip()
    candidates = [
        Path(configured).expanduser() if configured else None,
        APP_DIR / "Data" / "validated_original_engine",
        APP_DIR / "Data" / "forecast_engine",
        APP_DIR / "validated_original_engine",
        APP_DIR / "forecast_engine",
        Path.cwd() / "Data" / "validated_original_engine",
        Path.cwd() / "Data" / "forecast_engine",
    ]
    for candidate in candidates:
        if candidate and all((candidate / filename).is_file() for filename in REQUIRED_FILES.values()):
            return candidate.resolve()
    return (APP_DIR / "Data" / "forecast_engine").resolve()


@st.cache_data(show_spinner=False)
def load_data(directory: str) -> dict[str, Any]:
    root = Path(directory)
    frames: dict[str, Any] = {}
    for key, filename in REQUIRED_FILES.items():
        path = root / filename
        if key == "summary":
            with path.open("r", encoding="utf-8") as file:
                frames[key] = json.load(file)
        else:
            frames[key] = pd.read_csv(path, low_memory=False)
    for frame_name, columns in {
        "daily": ["timestamp"],
        "future": ["generated_at_utc", "as_of_date", "forecast_date"],
        "status": ["calendar_start", "calendar_end"],
    }.items():
        for column in columns:
            if column in frames[frame_name]:
                frames[frame_name][column] = pd.to_datetime(frames[frame_name][column], errors="coerce", utc=False)
    for name in ("daily", "future", "comparison", "status"):
        frame = frames[name]
        if "symbol" in frame:
            frame["symbol"] = frame["symbol"].astype("string").str.strip().str.lower()
        if "name" in frame:
            frame["name"] = frame["name"].astype("string").str.strip()
    numeric = {
        "daily": ["price_usd", "vol_24h"],
        "future": [
            "horizon_days", "data_age_days", "current_price", "predicted_price",
            "predicted_return_pct", "prediction_lower_95_error_band",
            "prediction_upper_95_error_band", "confidence_score", "annualised_volatility",
            "prediction_lower_empirical_band", "prediction_upper_empirical_band",
            "typical_absolute_percentage_error", "high_absolute_percentage_error",
            "model_MAPE", "model_sMAPE", "model_RMSPE", "model_MASE",
            "forecast_open", "forecast_high", "forecast_low", "forecast_close",
            "forecast_change_1d_pct",
        ],
        "comparison": [
            "horizon_days", "train_rows", "test_rows", "mae", "rmse", "mape",
            "smape", "rmspe", "mase", "absolute_percentage_error_p50",
            "absolute_percentage_error_p90", "directional_accuracy",
        ],
    }
    for name, columns in numeric.items():
        for column in columns:
            if column in frames[name]:
                frames[name][column] = pd.to_numeric(frames[name][column], errors="coerce")
    return frames


def locate_external_comparison(current_directory: Path) -> Path | None:
    """Locate the independent validation metrics without making them mandatory."""

    data_root = current_directory.parent
    candidates = [
        data_root / "validated_external_engine" / "model_comparison_daily.csv",
        data_root / "external_validation_engine" / "model_comparison_daily.csv",
    ]
    return next((path.resolve() for path in candidates if path.is_file()), None)


@st.cache_data(show_spinner=False)
def load_comparison_file(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    if "symbol" in frame:
        frame["symbol"] = frame["symbol"].astype("string").str.strip().str.lower()
    if "model" in frame:
        frame["model"] = frame["model"].astype("string").str.strip()
    for column in [
        "horizon_days", "train_rows", "test_rows", "mae", "rmse", "mape",
        "smape", "rmspe", "mase", "absolute_percentage_error_p50",
        "absolute_percentage_error_p90", "directional_accuracy",
    ]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def comparable_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep only robust, common validation horizons and usable metric rows."""

    if frame.empty:
        return frame.copy()
    valid = frame.copy()
    valid = valid.loc[
        valid.get("status", pd.Series("", index=valid.index)).eq("success")
        & pd.to_numeric(valid.get("test_rows"), errors="coerce").ge(5)
        & pd.to_numeric(valid.get("horizon_days"), errors="coerce").isin([1, 3, 7, 14])
    ].copy()
    if "eligible_for_comparison" in valid:
        eligibility = valid["eligible_for_comparison"].astype("string").str.lower()
        valid = valid.loc[eligibility.isin(["true", "1", "yes"])]
    required_models = {"Naive", "ARIMA", "XGBoost"}
    common_groups = (
        valid.groupby(["symbol", "horizon_days"])["model"]
        .agg(lambda values: required_models.issubset(set(values)))
    )
    common_groups = common_groups.loc[common_groups].reset_index()[
        ["symbol", "horizon_days"]
    ]
    if common_groups.empty:
        return valid.iloc[0:0].copy()
    return valid.merge(common_groups, on=["symbol", "horizon_days"], how="inner")


def weighted_model_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate percentage errors while respecting each row's test sample."""

    valid = comparable_metrics(frame)
    rows: list[dict[str, Any]] = []
    for model, group in valid.groupby("model"):
        weights = pd.to_numeric(group["test_rows"], errors="coerce").fillna(0)

        def weighted(column: str) -> float:
            if column not in group or weights.sum() <= 0:
                return np.nan
            values = pd.to_numeric(group[column], errors="coerce")
            mask = values.notna() & weights.gt(0)
            return float(np.average(values[mask], weights=weights[mask])) if mask.any() else np.nan

        rows.append({
            "model": str(model),
            "mape": weighted("mape"),
            "smape": weighted("smape"),
            "rmspe": weighted("rmspe"),
            "mase": weighted("mase"),
            "median_mae": float(
                pd.to_numeric(group.get("mae"), errors="coerce").median()
            ),
            "median_rmse": float(
                pd.to_numeric(group.get("rmse"), errors="coerce").median()
            ),
            "test_predictions": int(weights.sum()),
            "asset_horizon_groups": int(len(group)),
        })
    return pd.DataFrame(rows)


def finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def money(value: Any) -> str:
    if not finite(value):
        return "—"
    number = float(value)
    if abs(number) >= 1000:
        return f"${number:,.2f}"
    if abs(number) >= 1:
        return f"${number:,.4f}"
    if abs(number) >= .01:
        return f"${number:,.6f}"
    return f"${number:,.10f}"


def pct(value: Any, signed: bool = True) -> str:
    if not finite(value):
        return "—"
    return f"{float(value):+.2f}%" if signed else f"{float(value):.2f}%"


def compact(value: Any) -> str:
    if not finite(value):
        return "—"
    number = float(value)
    for limit, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(number) >= limit:
            return f"{number / limit:.2f}{suffix}"
    return f"{number:,.2f}"


def rgba(hex_color: str, alpha: float) -> str:
    """Convert a Streamlit colour-picker value to a safe CSS rgba colour."""

    value = str(hex_color).lstrip("#")
    if len(value) != 6 or any(character not in "0123456789abcdefABCDEF" for character in value):
        value = "43d9ff"
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{float(np.clip(alpha, 0, 1)):.3f})"


def metric(label: str, value: str, note: str = "", tone: str = "") -> str:
    return (
        f'<div class="metric"><div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value {html.escape(tone)}">{html.escape(value)}</div>'
        f'<div class="metric-note">{html.escape(note)}</div></div>'
    )


def binance_pair(symbol: str) -> str | None:
    base = str(symbol).strip().upper()
    aliases: dict[str, str | None] = {
        "USDT": None, "BSC-USD": None, "WETH": "ETH", "WBTC": "WBTC",
        "BTCB": "BTC", "MATIC": "POL",
    }
    if base in aliases:
        base = aliases[base]
    elif base.endswith("-USD"):
        base = base[:-4]
    if not base:
        return None
    return f"{base.replace('-', '').replace('_', '')}USDT"


@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_universe(symbols: tuple[str, ...]) -> tuple[pd.DataFrame, str]:
    if os.getenv("CRYPTO_DASHBOARD_OFFLINE", "").strip() == "1":
        return pd.DataFrame(columns=LIVE_COLUMNS), "Offline test mode"
    pair_map = {pair: symbol for symbol in symbols if (pair := binance_pair(symbol))}
    try:
        response = requests.get(f"{BINANCE_MARKET_BASE}/api/v3/ticker/24hr", timeout=8)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected market response")
        rows = []
        for item in payload:
            pair = str(item.get("symbol", ""))
            if pair in pair_map:
                rows.append({
                    "symbol": pair_map[pair], "pair": pair,
                    "live_price": pd.to_numeric(item.get("lastPrice"), errors="coerce"),
                    "change_24h": pd.to_numeric(item.get("priceChangePercent"), errors="coerce"),
                    "high_24h": pd.to_numeric(item.get("highPrice"), errors="coerce"),
                    "low_24h": pd.to_numeric(item.get("lowPrice"), errors="coerce"),
                    "quote_volume": pd.to_numeric(item.get("quoteVolume"), errors="coerce"),
                    "live_updated_at": pd.to_datetime(item.get("closeTime"), unit="ms", errors="coerce", utc=True),
                })
        return pd.DataFrame(rows, columns=LIVE_COLUMNS), ""
    except (requests.RequestException, ValueError, TypeError) as error:
        return pd.DataFrame(columns=LIVE_COLUMNS), f"Live market unavailable: {error}"


@st.cache_data(ttl=180, show_spinner=False)
def fetch_candles(symbol: str, interval: str, limit: int) -> tuple[pd.DataFrame, str]:
    pair = binance_pair(symbol)
    if not pair:
        return pd.DataFrame(), "No mapped public spot pair"
    if os.getenv("CRYPTO_DASHBOARD_OFFLINE", "").strip() == "1":
        return pd.DataFrame(), "Offline test mode"
    try:
        response = requests.get(
            f"{BINANCE_MARKET_BASE}/api/v3/klines",
            params={"symbol": pair, "interval": interval, "limit": int(np.clip(limit, 1, 1000))},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        rows = [{
            "timestamp": pd.to_datetime(item[0], unit="ms", utc=True).tz_localize(None),
            "open": float(item[1]), "high": float(item[2]), "low": float(item[3]),
            "close": float(item[4]), "volume": float(item[5]),
        } for item in payload]
        return pd.DataFrame(rows), ""
    except (requests.RequestException, ValueError, TypeError, IndexError) as error:
        return pd.DataFrame(), f"Candles unavailable: {error}"


def local_candles(symbol: str) -> pd.DataFrame:
    frame = daily.loc[daily["symbol"].eq(symbol)].sort_values("timestamp").copy()
    if frame.empty:
        return frame
    frame = frame.rename(columns={"price_usd": "close", "vol_24h": "volume"})
    frame["open"] = frame["close"].shift(1).fillna(frame["close"])
    spread = frame["close"].pct_change(fill_method=None).abs().rolling(7, min_periods=1).mean().fillna(.01)
    frame["high"] = frame[["open", "close"]].max(axis=1) * (1 + spread * .25)
    frame["low"] = frame[["open", "close"]].min(axis=1) * (1 - spread * .25)
    return frame[["timestamp", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])


def indicators(history: pd.DataFrame) -> dict[str, float]:
    if history.empty:
        return {}
    close = pd.to_numeric(history["close"], errors="coerce").dropna()
    if close.empty:
        return {}
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gains.div(losses.replace(0, np.nan)))
    returns = close.pct_change(fill_method=None).dropna()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    volume = pd.to_numeric(history.get("volume"), errors="coerce")
    volume_ratio = (
        float(volume.iloc[-1] / volume.tail(20).mean())
        if len(volume) >= 20 and finite(volume.tail(20).mean()) and volume.tail(20).mean() > 0
        else np.nan
    )
    high = pd.to_numeric(history.get("high"), errors="coerce")
    low = pd.to_numeric(history.get("low"), errors="coerce")
    previous_close = pd.to_numeric(history.get("close"), errors="coerce").shift(1)
    true_range = pd.concat(
        [(high - low).abs(), (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / 14, adjust=False).mean()

    def move(period: int) -> float:
        return float((close.iloc[-1] / close.iloc[-period - 1] - 1) * 100) if len(close) > period else np.nan

    return {
        "last": float(close.iloc[-1]), "move_1": move(1), "move_7": move(7), "move_30": move(30),
        "rsi": float(rsi.iloc[-1]) if len(rsi) and finite(rsi.iloc[-1]) else np.nan,
        "rsi_previous": float(rsi.iloc[-2]) if len(rsi) > 1 and finite(rsi.iloc[-2]) else np.nan,
        "sma20": float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else np.nan,
        "sma50": float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else np.nan,
        "macd": float(macd.iloc[-1]) if len(macd) and finite(macd.iloc[-1]) else np.nan,
        "macd_signal": float(macd_signal.iloc[-1]) if len(macd_signal) and finite(macd_signal.iloc[-1]) else np.nan,
        "volume_ratio": volume_ratio,
        "atr_pct": float(atr.iloc[-1] / close.iloc[-1] * 100) if len(atr) and finite(atr.iloc[-1]) and close.iloc[-1] > 0 else np.nan,
        "volatility": float(returns.tail(30).std(ddof=1) * np.sqrt(365) * 100) if len(returns) > 1 else np.nan,
    }


def forecast_path(symbol: str, anchor_price: float) -> tuple[pd.DataFrame, bool]:
    coin = future.loc[
        future["symbol"].eq(symbol) & future["status"].eq("FORECAST_GENERATED")
    ].sort_values("horizon_days").drop_duplicates("horizon_days", keep="last").copy()
    if coin.empty or not finite(anchor_price):
        return pd.DataFrame(), False
    coin = coin.loc[coin["horizon_days"].between(1, 30)]
    if coin.empty:
        return pd.DataFrame(), False
    data_age = pd.to_numeric(coin.get("data_age_days"), errors="coerce").min()
    latest_target = pd.to_datetime(coin["forecast_date"], errors="coerce").max()
    is_fresh = finite(data_age) and float(data_age) <= FORECAST_FRESHNESS_DAYS and pd.notna(latest_target) and latest_target > pd.Timestamp.now().normalize()
    base_price = pd.to_numeric(coin["current_price"], errors="coerce").replace(0, np.nan)
    returns = pd.to_numeric(coin["predicted_return_pct"], errors="coerce")
    implied = float(anchor_price) * (1 + returns / 100)
    horizons = pd.to_numeric(coin["horizon_days"], errors="coerce").astype(int).to_numpy()
    full_days = np.arange(1, 31)
    full_close = np.interp(full_days, np.r_[0, horizons], np.r_[float(anchor_price), implied.to_numpy(dtype=float)])
    raw_confidence = pd.to_numeric(coin.get("confidence_score"), errors="coerce")
    if raw_confidence.notna().any():
        full_confidence = np.interp(full_days, horizons, raw_confidence.fillna(raw_confidence.median()).to_numpy(dtype=float))
    else:
        full_confidence = np.full(30, np.nan)
    lower_column = (
        "prediction_lower_empirical_band"
        if "prediction_lower_empirical_band" in coin
        else "prediction_lower_95_error_band"
    )
    upper_column = (
        "prediction_upper_empirical_band"
        if "prediction_upper_empirical_band" in coin
        else "prediction_upper_95_error_band"
    )
    raw_lower = pd.to_numeric(coin.get(lower_column), errors="coerce")
    raw_upper = pd.to_numeric(coin.get(upper_column), errors="coerce")
    lower_ratio = raw_lower.div(base_price).replace([np.inf, -np.inf], np.nan)
    upper_ratio = raw_upper.div(base_price).replace([np.inf, -np.inf], np.nan)
    if lower_ratio.notna().any() and upper_ratio.notna().any():
        full_low_band = float(anchor_price) * np.interp(full_days, horizons, lower_ratio.fillna(1).to_numpy())
        full_high_band = float(anchor_price) * np.interp(full_days, horizons, upper_ratio.fillna(1).to_numpy())
    else:
        scale = np.linspace(.012, .07, 30)
        full_low_band = full_close * (1 - scale)
        full_high_band = full_close * (1 + scale)
    opens = np.r_[float(anchor_price), full_close[:-1]]
    step_move = np.divide(full_close, opens, out=np.ones_like(full_close), where=opens > 0) - 1
    recent_vol = pd.to_numeric(coin.get("annualised_volatility"), errors="coerce").dropna()
    daily_wick = float(np.clip((recent_vol.iloc[-1] if not recent_vol.empty else .7) / np.sqrt(365) * .3, .002, .08))
    path = pd.DataFrame({
        "day": full_days,
        "date": pd.Timestamp.now().normalize() + pd.to_timedelta(full_days, unit="D"),
        "open": opens,
        "close": full_close,
        "high": np.maximum(opens, full_close) * (1 + daily_wick),
        "low": np.minimum(opens, full_close) * (1 - daily_wick),
        "lower": np.minimum(full_low_band, full_close),
        "upper": np.maximum(full_high_band, full_close),
        "step_pct": step_move * 100,
        "confidence": full_confidence,
    })
    return path, bool(is_fresh)


def decision_score(
    stats: dict[str, float],
    path: pd.DataFrame,
    model_fresh: bool,
    decision_day: int = 7,
) -> dict[str, Any]:
    """Build a normalized multi-factor rating from inspectable market evidence."""

    components: list[dict[str, Any]] = []

    def add_factor(name: str, group: str, rating: float, weight: float, detail: str) -> None:
        if finite(rating):
            bounded = float(np.clip(rating, -1, 1))
            components.append({
                "factor": name,
                "group": group,
                "rating": bounded,
                "weight": float(weight),
                "contribution": bounded * float(weight),
                "detail": detail,
            })

    last, sma20, sma50 = stats.get("last"), stats.get("sma20"), stats.get("sma50")
    rsi, rsi_previous = stats.get("rsi"), stats.get("rsi_previous")
    macd, macd_signal = stats.get("macd"), stats.get("macd_signal")
    move_7, move_30 = stats.get("move_7"), stats.get("move_30")
    volume_ratio = stats.get("volume_ratio")

    if finite(last) and finite(sma20):
        add_factor("Price / SMA20", "Trend", 1 if last > sma20 else -1, 18, "Above SMA20" if last > sma20 else "Below SMA20")
    if finite(sma20) and finite(sma50):
        add_factor("SMA20 / SMA50", "Trend", 1 if sma20 > sma50 else -1, 14, "Bullish alignment" if sma20 > sma50 else "Bearish alignment")
    if finite(rsi) and finite(rsi_previous):
        rsi_rating = 1 if rsi < 30 and rsi > rsi_previous else -1 if rsi > 70 and rsi < rsi_previous else 0
        add_factor("RSI reversal", "Oscillator", rsi_rating, 12, f"RSI {rsi:.1f}")
    if finite(macd) and finite(macd_signal):
        add_factor("MACD", "Oscillator", 1 if macd > macd_signal else -1, 15, "Above signal" if macd > macd_signal else "Below signal")
    if finite(move_7):
        momentum_rating = 1 if move_7 > 1 else -1 if move_7 < -1 else 0
        add_factor("7D momentum", "Momentum", momentum_rating, 13, f"{move_7:+.2f}%")
    if finite(volume_ratio) and finite(move_7):
        volume_rating = np.sign(move_7) if volume_ratio >= 1.10 and abs(move_7) >= 1 else 0
        add_factor("Volume confirmation", "Momentum", volume_rating, 8, f"{volume_ratio:.2f}× average")

    model_move = np.nan
    model_weight = 20 if model_fresh else 8
    if not path.empty:
        horizon_row = path.loc[path["day"].eq(int(np.clip(decision_day, 1, 30)))]
        if not horizon_row.empty and path["open"].iloc[0] > 0:
            model_move = (float(horizon_row.iloc[0]["close"]) / float(path["open"].iloc[0]) - 1) * 100
            model_rating = 1 if model_move > 1 else -1 if model_move < -1 else 0
            model_confidence = horizon_row.iloc[0].get("confidence", np.nan)
            confidence_multiplier = float(np.clip(model_confidence / 100, .35, 1.0)) if finite(model_confidence) else .35
            effective_model_weight = model_weight * confidence_multiplier
            add_factor(
                f"Day {decision_day} model path",
                "Forecast",
                model_rating,
                effective_model_weight,
                f"{model_move:+.2f}% · strength {model_confidence:.0f}/100" if finite(model_confidence) else f"{model_move:+.2f}% · limited strength",
            )

    active_weight = sum(item["weight"] for item in components)
    raw_score = sum(item["contribution"] for item in components)
    score = float(np.clip(raw_score / active_weight * 100, -100, 100)) if active_weight else 0.0
    coverage = float(np.clip(active_weight / 100 * 100, 0, 100))
    evidence_strength = float(np.clip(abs(score) * .72 + coverage * .28, 0, 100))

    atr_pct = stats.get("atr_pct", np.nan)
    volatility = stats.get("volatility", np.nan)
    if finite(atr_pct) and atr_pct >= 6 or finite(volatility) and volatility >= 120:
        risk = "EXTREME"
    elif finite(atr_pct) and atr_pct >= 3.5 or finite(volatility) and volatility >= 80:
        risk = "HIGH"
    elif finite(atr_pct) and atr_pct >= 1.8 or finite(volatility) and volatility >= 45:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    if score >= 50:
        action = "STRONG BUY WATCH"
    elif score >= 10:
        action = "BUY WATCH"
    elif score <= -50:
        action = "STRONG SELL WATCH"
    elif score <= -10:
        action = "SELL WATCH"
    else:
        action = "WAIT"

    # A stale model may inform the scenario display, but never independently
    # upgrades the decision to a strong recommendation.
    if (not model_fresh or decision_day >= 30) and action.startswith("STRONG"):
        action = "BUY WATCH" if score > 0 else "SELL WATCH"

    component_frame = pd.DataFrame(components)
    if not component_frame.empty:
        component_frame = component_frame.sort_values("contribution", kind="mergesort")
    return {
        "score": score,
        "normalized": score / 100,
        "action": action,
        "evidence_strength": evidence_strength,
        "coverage": coverage,
        "risk": risk,
        "model_move": model_move,
        "components": component_frame,
        "model_fresh": model_fresh,
        "move_30": move_30,
    }


def style_chart(fig: go.Figure, height: int = 500) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height, margin=dict(l=24, r=24, t=56, b=58),
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=CHART_FONT, size=13, family="Inter, Segoe UI, sans-serif"),
        title_font=dict(color=CHART_TITLE, size=17),
        legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)", y=-.16, font=dict(color=CHART_FONT, size=12)),
        hoverlabel=dict(bgcolor=CHART_HOVER_BG, bordercolor="#d9e0e8", font_color=CHART_HOVER_FONT, font_size=12), hovermode="x unified",
        transition=dict(duration=450, easing="cubic-in-out"),
    )
    axis_style = dict(
        gridcolor=CHART_GRID,
        linecolor="#cfd6df",
        tickcolor="#9aa8b7",
        tickfont=dict(color=CHART_FONT, size=12),
        title_font=dict(color=CHART_FONT, size=13),
        zeroline=False,
        automargin=True,
    )
    fig.update_xaxes(**axis_style, showspikes=True, spikemode="across", spikecolor="#8b98a8")
    fig.update_yaxes(**axis_style)
    return fig


def decision_gauge(result: dict[str, Any]) -> go.Figure:
    """Render a five-zone professional market rating dial."""

    score = float(result["score"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        number={"suffix": "", "font": {"size": 42, "color": CHART_TITLE}},
        delta={"reference": 0, "relative": False, "increasing": {"color": POSITIVE_COLOR}, "decreasing": {"color": NEGATIVE_COLOR}},
        title={"text": f"{result['action']}<br><span style='font-size:12px;color:{CHART_FONT}'>NORMALIZED MARKET RATING</span>"},
        gauge={
            "axis": {
                "range": [-100, 100],
                "tickvals": [-100, -50, -10, 10, 50, 100],
                "ticktext": ["Strong sell", "Sell", "Neutral", "Neutral", "Buy", "Strong buy"],
                "tickfont": {"size": 10, "color": CHART_FONT},
            },
            "bar": {"color": CHART_TITLE, "thickness": .16},
            "bgcolor": CHART_BG,
            "borderwidth": 0,
            "steps": [
                {"range": [-100, -50], "color": "rgba(255,85,119,.62)"},
                {"range": [-50, -10], "color": "rgba(255,128,102,.42)"},
                {"range": [-10, 10], "color": "rgba(255,200,87,.24)"},
                {"range": [10, 50], "color": "rgba(67,217,255,.35)"},
                {"range": [50, 100], "color": "rgba(40,224,160,.58)"},
            ],
            "threshold": {"line": {"color": ACCENT_COLOR, "width": 4}, "thickness": .8, "value": score},
        },
    ))
    fig.update_layout(title="Decision spectrum")
    return style_chart(fig, 390)


def contribution_chart(result: dict[str, Any]) -> go.Figure:
    """Show exactly which factors pushed the signal toward buy or sell."""

    frame = result["components"].copy()
    if frame.empty:
        return style_chart(go.Figure(), 390)
    colors = np.where(
        frame["contribution"].gt(0),
        POSITIVE_COLOR,
        np.where(frame["contribution"].lt(0), NEGATIVE_COLOR, "#8896a8"),
    )
    fig = go.Figure(go.Bar(
        x=frame["contribution"],
        y=frame["factor"],
        orientation="h",
        marker_color=colors,
        text=frame["contribution"].map(lambda value: f"{value:+.1f}" if abs(value) >= .1 else ""),
        textposition="outside",
        textfont=dict(color=CHART_FONT, size=11),
        cliponaxis=False,
        customdata=np.c_[frame["detail"], frame["group"], frame["rating"], frame["weight"]],
        hovertemplate="%{y}<br>%{customdata[0]}<br>Group: %{customdata[1]}<br>Rating: %{customdata[2]:+.0f}<br>Weight: %{customdata[3]:.0f}<br>Contribution: %{x:+.1f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=CHART_GRID, line_width=1)
    fig.update_layout(title="Why the indicator moved", xaxis_title="Signal contribution  ·  sell ← 0 → buy", yaxis_title=None)
    return style_chart(fig, 430)


def ticker(live: pd.DataFrame) -> None:
    if live.empty:
        return
    movers = live.reindex(live["change_24h"].abs().sort_values(ascending=False).index).head(18)
    items = []
    for row in movers.itertuples(index=False):
        tone = "up" if row.change_24h >= 0 else "down"
        items.append(f'<span class="ticker-item"><b>{html.escape(str(row.symbol).upper())}</b> {html.escape(money(row.live_price))} <span class="{tone}">{row.change_24h:+.2f}%</span></span>')
    st.markdown(f'<div class="ticker-shell"><div class="ticker-track">{"".join(items)}</div></div>', unsafe_allow_html=True)


def forecast_candles(path: pd.DataFrame, title: str, selected_day: int | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=path["date"], y=path["upper"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=path["date"], y=path["lower"], fill="tonexty", fillcolor="rgba(139,124,255,.10)", line=dict(width=0), name="Scenario range"))
    fig.add_trace(go.Candlestick(
        x=path["date"], open=path["open"], high=path["high"], low=path["low"], close=path["close"],
        name="Daily forecast", increasing_line_color=POSITIVE_COLOR, decreasing_line_color=NEGATIVE_COLOR,
        increasing_fillcolor="rgba(0,127,95,.46)", decreasing_fillcolor="rgba(201,47,72,.46)",
    ))
    if selected_day:
        point = path.loc[path["day"].eq(selected_day)].iloc[0]
        fig.add_vline(x=point["date"].timestamp() * 1000, line_color=ACCENT_COLOR, line_width=1.5, line_dash="dot")
    fig.update_layout(title=title, yaxis_title="USD", xaxis_rangeslider_visible=False)
    return style_chart(fig, 490)


DATA_DIR = locate_data_directory()
missing = [name for name in REQUIRED_FILES.values() if not (DATA_DIR / name).is_file()]
if missing:
    st.error("Forecast outputs were not found.")
    st.code(str(DATA_DIR), language=None)
    st.caption("Keep app.py beside Data → forecast_engine, then run the forecast engine once.")
    st.stop()

loaded = load_data(str(DATA_DIR))
daily: pd.DataFrame = loaded["daily"]
future: pd.DataFrame = loaded["future"]
comparison: pd.DataFrame = loaded["comparison"]
status: pd.DataFrame = loaded["status"]
summary: dict[str, Any] = loaded["summary"]
external_comparison_path = locate_external_comparison(DATA_DIR)
external_comparison = (
    load_comparison_file(str(external_comparison_path))
    if external_comparison_path is not None
    else pd.DataFrame()
)

assets = status[["symbol", "name"]].drop_duplicates("symbol").dropna(subset=["symbol"]).sort_values("name")
labels = {f"{row.name} · {str(row.symbol).upper()}": str(row.symbol) for row in assets.itertuples(index=False)}
label_list = list(labels)
default_label = next((label for label in label_list if label.endswith("· BTC")), label_list[0])

st.sidebar.markdown('<div class="brand"><div class="brand-name">◈ Crypto<span>Forecast</span></div><div class="brand-sub">MARKET INTELLIGENCE TERMINAL</div></div>', unsafe_allow_html=True)
page = st.sidebar.radio(
    "Workspace",
    ["Live Terminal", "Signal Reactor", "Market Radar", "Model Health", "Easy Mode"],
)
selected_label = st.sidebar.selectbox("Market", label_list, index=label_list.index(default_label))
symbol = labels[selected_label]
live_enabled = st.sidebar.toggle("Live market", value=True)
if st.sidebar.button("Refresh market", width="stretch"):
    fetch_live_universe.clear(); fetch_candles.clear(); st.rerun()

selected_theme = WHITE_THEME
ACCENT_COLOR = selected_theme["accent"]
SECONDARY_COLOR = selected_theme["secondary"]
INK_COLOR = "#111827"
MUTED_COLOR = "#526174"
PANEL_COLOR = "rgba(255,255,255,.96)"
PANEL_SOFT = "rgba(244,247,251,.98)"
CHART_BG = "#ffffff"
CHART_FONT = "#405166"
CHART_TITLE = "#111827"
CHART_GRID = "#e6eaf0"
CHART_HOVER_BG = "#ffffff"
CHART_HOVER_FONT = "#111827"
theme_css = f"""
<style>
    :root {{
        --night:{selected_theme['background']};
        --cyan:{ACCENT_COLOR};
        --violet:{SECONDARY_COLOR};
        --line:#e3e8ef;
        --ink:{INK_COLOR};
        --muted:{MUTED_COLOR};
        --panel:{PANEL_COLOR};
        --green:{POSITIVE_COLOR};
        --red:{NEGATIVE_COLOR};
    }}
    .stApp {{
        background:#f7f8fa;
        color:{INK_COLOR};
        font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    }}
    [data-testid="stSidebar"] {{
        background:#ffffff;
        border-right:1px solid #e3e8ef;
    }}
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ color:{INK_COLOR}; }}
    .stApp p, .stApp label, .stApp [data-testid="stCaptionContainer"] {{ color:{INK_COLOR}; }}
    .stApp [data-testid="stWidgetLabel"] p {{ color:{INK_COLOR};font-weight:650; }}
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stBaseButton-secondary"] {{
        background:#ffffff !important;
        color:{INK_COLOR} !important;
        border:1px solid #d7dee7 !important;
        box-shadow:none !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover {{
        background:#f3f6f8 !important;
        border-color:#aeb9c6 !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] * {{ color:{INK_COLOR} !important; }}
    [data-testid="stSelectbox"] svg {{ fill:{MUTED_COLOR} !important;color:{MUTED_COLOR} !important; }}
    [data-baseweb="input"], [data-testid="stNumberInput"] input {{
        background:#ffffff !important;
        color:{INK_COLOR} !important;
        border-color:#d7dee7 !important;
    }}
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"],
    button[kind="segmented_control"] {{
        background:#ffffff !important;
        color:#263648 !important;
        border:1px solid #d7dee7 !important;
        box-shadow:none !important;
    }}
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"] p,
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"] span,
    button[kind="segmented_control"] p,
    button[kind="segmented_control"] span {{ color:inherit !important; }}
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover,
    button[kind="segmented_control"]:hover {{
        background:#f0f5f3 !important;
        color:#00694f !important;
    }}
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"][data-selected],
    button[kind="segmented_controlActive"] {{
        background:#e5f6f1 !important;
        color:#00694f !important;
        border-color:{ACCENT_COLOR} !important;
        font-weight:700 !important;
    }}
    [data-testid="stCheckbox"] [role="switch"] {{
        background:#d8dee6 !important;
        border-color:#c6ced8 !important;
    }}
    [data-testid="stCheckbox"] [role="switch"][aria-checked="true"],
    [data-testid="stCheckbox"] [data-selected] {{ background:{ACCENT_COLOR} !important; }}
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
    [data-testid="stSlider"] p, [data-testid="stNumberInput"] label {{ color:{INK_COLOR}; }}
    [data-testid="stSlider"] [role="slider"] {{ background:{ACCENT_COLOR} !important; }}
    [data-baseweb="popover"], [data-baseweb="menu"] {{
        background:#ffffff !important;
        color:{INK_COLOR} !important;
    }}
    [role="option"] {{ color:{INK_COLOR};background:#ffffff; }}
    [role="option"]:hover {{ background:{rgba(ACCENT_COLOR, .10)}; }}
    h1,h2,h3,.brand-name,.terminal-title {{ color:{INK_COLOR}; }}
    .terminal-sub,.metric-label,.metric-note,.signal-score,.easy-label,.fine-print {{ color:{MUTED_COLOR}; }}
    div[data-testid="stPlotlyChart"] {{
        background:#ffffff;
        border:1px solid #e3e8ef;
        box-shadow:0 8px 24px rgba(17,24,39,.06);
    }}
    .metric,.trade-ticket,.easy-call {{ background:#ffffff;border-color:#e3e8ef;box-shadow:0 5px 16px rgba(17,24,39,.045); }}
    .metric-value,.ticket-result,.micro-value,.easy-value {{ color:{INK_COLOR}; }}
    .ticker-shell {{ background:{PANEL_SOFT}; }}
    .ticker-item,.pill {{ color:{INK_COLOR}; }}
    .pill,.micro,.radar-card {{ background:{PANEL_SOFT}; }}
    .brand-sub,.micro-label {{ color:{MUTED_COLOR}; }}
    .pill-live {{ color:#087653; }}
    .pill-model {{ color:#3f55a4; }}
    .brand-name span,.live-line,.signal-kicker,.ticket-head {{ color:#007a5a; }}
    .brand-name span {{ text-shadow:none; }}
    .terminal-head {{
        border-color:#e3e8ef;
        background:#ffffff;
        box-shadow:0 8px 24px rgba(17,24,39,.06);
    }}
    .terminal-head:after {{ display:none; }}
    .signal-core {{ border-color:#d9e3df;background:radial-gradient(circle,rgba(0,127,95,.09),#ffffff 66%); }}
    .signal-core:before {{ border-color:{rgba(ACCENT_COLOR, .48)}; }}
    .signal-core:after {{ border-color:{rgba(SECONDARY_COLOR, .38)};border-left-color:transparent; }}
    .micro {{ border-left-color:{rgba(ACCENT_COLOR, .62)}; }}
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)

tracked = tuple(assets["symbol"].astype(str))
live_market, live_error = fetch_live_universe(tracked) if live_enabled else (pd.DataFrame(columns=LIVE_COLUMNS), "Live market switched off")
live_coin = live_market.loc[live_market["symbol"].eq(symbol)]
live_row = live_coin.iloc[0] if not live_coin.empty else None
fallback_history = local_candles(symbol)
fallback_price = fallback_history["close"].iloc[-1] if not fallback_history.empty else np.nan
anchor_price = float(live_row["live_price"]) if live_row is not None and finite(live_row["live_price"]) else fallback_price
path, model_fresh = forecast_path(symbol, anchor_price)
model_mode = "CURRENT 30D SCENARIO" if model_fresh else "STALE SCENARIO · LOW WEIGHT"

st.sidebar.markdown('<div class="status-ribbon">', unsafe_allow_html=True)
if not live_market.empty:
    st.sidebar.markdown('<span class="pill pill-live"><span class="live-dot"></span>MARKET LIVE</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="pill">CACHED MARKET</span>', unsafe_allow_html=True)
st.sidebar.markdown(f'<span class="pill pill-model">{html.escape(model_mode)}</span>', unsafe_allow_html=True)
st.sidebar.caption("Scenario intelligence · No order execution")

ticker(live_market)

if page == "Live Terminal":
    timeframe = st.segmented_control(
        "Candle interval",
        ["1H · 24H", "4H · 72H", "1D · 1W", "7D · 1M", "1W · 1Y"],
        default="1D · 1W",
    )
    interval_map = {
        "1H · 24H": {"api": "5m", "bars": 288, "window": "24 hours", "bar": "1H", "detail": "5m", "lookback": 12, "tick": "%H:%M"},
        "4H · 72H": {"api": "15m", "bars": 288, "window": "72 hours", "bar": "4H", "detail": "15m", "lookback": 16, "tick": "%d %b\n%H:%M"},
        "1D · 1W": {"api": "1h", "bars": 168, "window": "1 week", "bar": "1D", "detail": "1H", "lookback": 24, "tick": "%a\n%d %b"},
        "7D · 1M": {"api": "4h", "bars": 180, "window": "1 month", "bar": "7D", "detail": "4H", "lookback": 42, "tick": "%d %b"},
        "1W · 1Y": {"api": "1d", "bars": 365, "window": "1 year", "bar": "1W", "detail": "1D", "lookback": 7, "tick": "%b %Y"},
    }
    interval_settings = interval_map[timeframe]
    interval, bars = interval_settings["api"], int(interval_settings["bars"])
    history, candle_error = fetch_candles(symbol, interval, bars) if live_enabled else (pd.DataFrame(), "")
    history_mode = f"{interval_settings['bar']} overview · {interval_settings['detail']} zoom detail · last {interval_settings['window']}"
    if history.empty:
        history = fallback_history.tail(bars)
        history_mode = f"Cached daily candles · last {min(len(history), bars)} observations"
    history = history.sort_values("timestamp").tail(bars).dropna(subset=["timestamp", "open", "high", "low", "close"])
    stats = indicators(history)
    lookback = int(interval_settings["lookback"])
    previous_close = float(history["close"].iloc[-lookback - 1]) if len(history) > lookback else np.nan
    latest_close = float(history["close"].iloc[-1]) if not history.empty else np.nan
    interval_change = latest_close - previous_close if finite(latest_close) and finite(previous_close) else np.nan
    interval_move = (latest_close / previous_close - 1) * 100 if finite(latest_close) and finite(previous_close) and previous_close > 0 else np.nan
    visible_change = (latest_close / float(history["close"].iloc[0]) - 1) * 100 if len(history) >= 2 and float(history["close"].iloc[0]) > 0 else np.nan
    bar_label = interval_settings["bar"] if "Cached" not in history_mode else "1D"
    st.markdown(f'<div class="terminal-head"><div class="live-line"><span class="live-dot"></span>{html.escape(str(symbol).upper())} / USDT · {html.escape(timeframe.upper())}</div><div class="terminal-title">{html.escape(selected_label)}</div><div class="terminal-sub">Scroll to zoom · {html.escape(str(interval_settings["detail"]))} sub-candles reveal movement inside the {html.escape(str(interval_settings["bar"]))} view</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-grid">' + metric("Market price", money(anchor_price), "Latest public spot", "") + metric(f"{bar_label} move", pct(interval_move), "Latest selected candle", "up" if finite(interval_move) and interval_move >= 0 else "down") + metric(f"{bar_label} change", ("+" if finite(interval_change) and interval_change >= 0 else "") + money(interval_change), "Absolute price change", "up" if finite(interval_change) and interval_change >= 0 else "down") + metric("Visible-period move", pct(visible_change), history_mode, "up" if finite(visible_change) and visible_change >= 0 else "down") + '</div>', unsafe_allow_html=True)

    terminal = go.Figure()
    terminal.add_trace(go.Candlestick(x=history["timestamp"], open=history["open"], high=history["high"], low=history["low"], close=history["close"], name="Market candles", increasing_line_color=POSITIVE_COLOR, decreasing_line_color=NEGATIVE_COLOR, increasing_fillcolor="rgba(0,127,95,.42)", decreasing_fillcolor="rgba(201,47,72,.42)"))
    trend_period = 20 if len(history) >= 40 else max(3, min(10, len(history) // 2))
    if len(history) >= trend_period:
        terminal.add_trace(go.Scatter(x=history["timestamp"], y=history["close"].rolling(trend_period).mean(), name=f"{trend_period}-candle trend", line=dict(color=ACCENT_COLOR, width=1.7)))
    terminal.update_layout(title=f"{str(symbol).upper()} market structure · {history_mode}", xaxis_rangeslider_visible=False, yaxis_title="USD", dragmode="zoom")
    if not history.empty:
        terminal.update_xaxes(
            range=[history["timestamp"].min(), history["timestamp"].max()],
            tickformat=str(interval_settings["tick"]),
            nticks=10,
        )
    st.plotly_chart(style_chart(terminal, 570), width="stretch", theme=None, config={"displaylogo": False, "scrollZoom": True})

elif page == "Signal Reactor":
    history, candle_error = fetch_candles(symbol, "1d", 365) if live_enabled else (pd.DataFrame(), "")
    if history.empty:
        history = fallback_history.tail(365)
    stats = indicators(history)
    day = st.slider("Decision horizon", 1, 30, 7)
    decision = decision_score(stats, path, model_fresh, day)
    score = float(decision["score"])
    action = str(decision["action"])
    action_tone = "up" if score >= 10 else "down" if score <= -10 else "warn"
    selected = path.loc[path["day"].eq(day)].iloc[0] if not path.empty else None
    target_price = selected["close"] if selected is not None else np.nan
    target_move = (target_price / anchor_price - 1) * 100 if finite(target_price) and anchor_price > 0 else np.nan

    st.markdown(f'<div class="terminal-head"><div class="live-line">SIGNAL REACTOR · DAY {day}</div><div class="terminal-title">Confluence before action</div><div class="terminal-sub">Trend · oscillators · momentum · volume · forecast path</div></div>', unsafe_allow_html=True)
    left, right = st.columns([.9, 1.25], gap="large")
    with left:
        st.markdown(f'<div class="signal-core"><div class="signal-content"><div class="signal-kicker">Decision status</div><div class="signal-action {action_tone}">{html.escape(action)}</div><div class="signal-score">RATING {score:+.0f} / 100</div></div></div>', unsafe_allow_html=True)
        freshness_label = "MODEL CURRENT" if model_fresh else "MODEL SCENARIO · LOW WEIGHT"
        st.markdown(f'<div class="status-ribbon"><span class="pill pill-model">{freshness_label}</span><span class="pill">RISK {html.escape(str(decision["risk"]))}</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="micro-grid">' + '<div class="micro"><div class="micro-label">Evidence strength</div><div class="micro-value">' + f'{decision["evidence_strength"]:.0f}/100' + '</div></div>' + '<div class="micro"><div class="micro-label">Day target</div><div class="micro-value">' + html.escape(money(target_price)) + '</div></div>' + '<div class="micro"><div class="micro-label">Projected move</div><div class="micro-value ' + ("up" if finite(target_move) and target_move >= 0 else "down") + '">' + html.escape(pct(target_move)) + '</div></div></div>', unsafe_allow_html=True)
    with right:
        st.plotly_chart(decision_gauge(decision), width="stretch", theme=None, config={"displayModeBar": False})

    chart_left, chart_right = st.columns([1.25, 1], gap="large")
    with chart_left:
        if path.empty:
            st.warning("Run the 30-day forecast engine to activate the decision path.")
        else:
            st.plotly_chart(forecast_candles(path, f"30-day decision path · focus day {day}", day), width="stretch", theme=None, config={"displaylogo": False})
    with chart_right:
        st.plotly_chart(contribution_chart(decision), width="stretch", theme=None, config={"displayModeBar": False})

    st.subheader(f"{action.title()} scenario calculator")
    mode = st.segmented_control("Action", ["BUY", "SELL"], default="BUY")
    ticket_left, ticket_right = st.columns([1, 1.25], gap="large")
    fee_pct = .10
    with ticket_left:
        if mode == "BUY":
            amount = st.number_input("Amount to spend (USD)", min_value=0.0, value=1000.0, step=100.0)
            fee = amount * fee_pct / 100
            units = (amount - fee) / anchor_price if anchor_price > 0 else 0.0
            future_value = units * target_price if finite(target_price) else np.nan
            delta = future_value - amount if finite(future_value) else np.nan
            headline, result = "Estimated coins received", f"{units:,.8f} {symbol.upper()}"
            compare_a, compare_b = amount, future_value
            compare_names = ["Spend now", f"Value on day {day}"]
        else:
            units = st.number_input(f"Coins to sell ({symbol.upper()})", min_value=0.0, value=1.0, step=.1, format="%.8f")
            gross = units * anchor_price
            fee = gross * fee_pct / 100
            result = money(gross - fee); headline = "Estimated cash received"
            held_value = units * target_price if finite(target_price) else np.nan
            delta = held_value - (gross - fee) if finite(held_value) else np.nan
            compare_a, compare_b = gross - fee, held_value
            compare_names = ["Sell now", f"Hold to day {day}"]
        st.markdown(f'<div class="trade-ticket"><div class="ticket-head">{html.escape(mode)} ESTIMATE</div><div class="metric-label">{html.escape(headline)}</div><div class="ticket-result">{html.escape(result)}</div><div class="metric-note">Estimated fee {fee_pct:.2f}% · {html.escape(money(fee))}</div><div class="metric-label" style="margin-top:.8rem">Scenario difference</div><div class="ticket-result {"up" if finite(delta) and delta >= 0 else "down"}">{html.escape(money(delta))}</div></div>', unsafe_allow_html=True)
    with ticket_right:
        comparison = pd.DataFrame({"Moment": compare_names, "USD": [compare_a, compare_b]})
        fig = px.bar(comparison, x="Moment", y="USD", color="Moment", text_auto=".3s", color_discrete_sequence=[ACCENT_COLOR, "#6b7c90"])
        fig.update_layout(title="Cash / position value comparison", showlegend=False, yaxis_title="USD", xaxis_title=None)
        st.plotly_chart(style_chart(fig, 360), width="stretch", theme=None, config={"displayModeBar": False})
    st.caption("Simulation only. Fees are adjustable assumptions; slippage, taxes and exchange rules are not included.")

elif page == "Market Radar":
    st.markdown('<div class="terminal-head"><div class="live-line"><span class="live-dot"></span>MARKET RADAR</div><div class="terminal-title">Movement scanner</div><div class="terminal-sub">Find pressure, volume and unusual moves quickly</div></div>', unsafe_allow_html=True)
    if live_market.empty:
        st.warning(f"Live radar is temporarily unavailable. {live_error}")
    else:
        radar = live_market.dropna(subset=["live_price", "change_24h"]).copy()
        radar["symbol_display"] = radar["symbol"].str.upper()
        radar["direction"] = np.where(radar["change_24h"] >= 0, "Rising", "Falling")
        top_up = radar.nlargest(1, "change_24h").iloc[0]
        top_down = radar.nsmallest(1, "change_24h").iloc[0]
        volume_leader = radar.nlargest(1, "quote_volume").iloc[0]
        st.markdown('<div class="metric-grid">' + metric("Fastest rise", f"{top_up.symbol_display} {pct(top_up.change_24h)}", "24-hour move", "up") + metric("Fastest fall", f"{top_down.symbol_display} {pct(top_down.change_24h)}", "24-hour move", "down") + metric("Volume leader", volume_leader.symbol_display, compact(volume_leader.quote_volume) + " USDT") + metric("Market pulse", f"{(radar.change_24h > 0).mean() * 100:.0f}% GREEN", "Connected spot pairs", "up" if (radar.change_24h > 0).mean() >= .5 else "down") + '</div>', unsafe_allow_html=True)
        left, right = st.columns([1.15, 1])
        with left:
            plot = radar.loc[radar["quote_volume"].gt(0)].copy()
            fig = px.scatter(plot, x="quote_volume", y="change_24h", size="quote_volume", color="direction", hover_name="symbol_display", log_x=True, color_discrete_map={"Rising": POSITIVE_COLOR, "Falling": NEGATIVE_COLOR}, title="Volume vs 24-hour movement")
            fig.update_layout(xaxis_title="Quote volume (log)", yaxis_title="24H move (%)")
            st.plotly_chart(style_chart(fig, 480), width="stretch", theme=None, config={"displaylogo": False})
        with right:
            movers = pd.concat([radar.nlargest(8, "change_24h"), radar.nsmallest(8, "change_24h")]).drop_duplicates("symbol")
            movers = movers.sort_values("change_24h")
            fig = go.Figure(go.Bar(x=movers["change_24h"], y=movers["symbol_display"], orientation="h", marker_color=np.where(movers["change_24h"] >= 0, POSITIVE_COLOR, NEGATIVE_COLOR), text=movers["change_24h"].map(lambda x: f"{x:+.2f}%"), textposition="outside"))
            fig.update_layout(title="Momentum extremes", xaxis_title="24H move (%)", yaxis_title=None)
            st.plotly_chart(style_chart(fig, 480), width="stretch", theme=None, config={"displayModeBar": False})
        st.subheader("Pressure alerts")
        alerts = radar.loc[radar["change_24h"].abs().ge(4)].copy()
        alerts["alert_magnitude"] = alerts["change_24h"].abs()
        alerts = alerts.sort_values("alert_magnitude", ascending=False).head(12)
        if alerts.empty:
            st.markdown('<div class="radar-card">No connected market crossed the ±4% pressure line.</div>', unsafe_allow_html=True)
        else:
            columns = st.columns(2)
            for index, row in enumerate(alerts.itertuples(index=False)):
                tone = "up" if row.change_24h >= 0 else "down"
                with columns[index % 2]:
                    st.markdown(f'<div class="radar-card"><b>{html.escape(str(row.symbol).upper())}</b> <span class="{tone}">{row.change_24h:+.2f}%</span><br><span class="metric-note">{html.escape(money(row.live_price))} · Volume {html.escape(compact(row.quote_volume))}</span></div>', unsafe_allow_html=True)

elif page == "Model Health":
    st.markdown(
        '<div class="terminal-head"><div class="live-line">MODEL HEALTH</div>'
        '<div class="terminal-title">Reliability across market conditions</div>'
        '<div class="terminal-sub">Validated percentage error · consistent 1D, 3D, 7D and 14D tests</div></div>',
        unsafe_allow_html=True,
    )

    current_summary = weighted_model_summary(comparison)
    independent_summary = weighted_model_summary(external_comparison)
    model_labels = {
        "Naive": ("VALIDATED BASELINE", "Reference model"),
        "ARIMA": ("VALIDATED", "Primary statistical model"),
        "XGBoost": ("EXPERIMENTAL", "Excluded from action signals"),
    }
    cards = st.columns(3)
    for column, model in zip(cards, ["Naive", "ARIMA", "XGBoost"]):
        current_row = current_summary.loc[current_summary["model"].eq(model)]
        external_row = independent_summary.loc[independent_summary["model"].eq(model)]
        current_mape = current_row["mape"].iloc[0] if not current_row.empty else np.nan
        external_mape = external_row["mape"].iloc[0] if not external_row.empty else np.nan
        mape_change = (
            float(external_mape) - float(current_mape)
            if finite(external_mape) and finite(current_mape)
            else np.nan
        )
        status_label, note = model_labels[model]
        with column:
            st.markdown(
                metric(
                    f"{model} · {status_label}",
                    pct(external_mape, signed=False),
                    (
                        f"Independent MAPE · change {mape_change:+.2f} pp · {note}"
                        if finite(mape_change)
                        else f"Independent MAPE · {note}"
                    ),
                    "warn" if model == "XGBoost" else "up",
                ),
                unsafe_allow_html=True,
            )

    if independent_summary.empty:
        st.warning(
            "Independent validation results were not found. Keep "
            "Data/validated_external_engine beside the current engine output."
        )
    else:
        selected_models = ["Naive", "ARIMA"]
        display = current_summary[
            ["model", "mape", "median_mae", "median_rmse"]
        ].rename(
            columns={
                "mape": "Original MAPE",
                "median_mae": "Original median MAE",
                "median_rmse": "Original median RMSE",
            }
        ).merge(
            independent_summary[
                ["model", "mape", "median_mae", "median_rmse"]
            ].rename(
                columns={
                    "mape": "External MAPE",
                    "median_mae": "External median MAE",
                    "median_rmse": "External median RMSE",
                }
            ),
            on="model",
            how="outer",
        )
        selected_display = display.loc[display["model"].isin(selected_models)].copy()

        mape_long = selected_display.melt(
            id_vars="model",
            value_vars=["Original MAPE", "External MAPE"],
            var_name="Dataset",
            value_name="MAPE",
        ).dropna(subset=["MAPE"])
        fig = px.bar(
            mape_long,
            x="model",
            y="MAPE",
            color="Dataset",
            barmode="group",
            text_auto=".2f",
            category_orders={"model": selected_models},
            color_discrete_sequence=[ACCENT_COLOR, SECONDARY_COLOR],
            title="Selected models · original vs unseen MAPE",
        )
        fig.update_layout(xaxis_title=None, yaxis_title="MAPE (%)")
        st.plotly_chart(
            style_chart(fig, 450),
            width="stretch",
            theme=None,
            config={"displayModeBar": False},
        )

        scale_columns = st.columns(2)
        scale_specs = [
            (
                "Median MAE by dataset",
                ["Original median MAE", "External median MAE"],
                "Median MAE (USD)",
                "MAE",
            ),
            (
                "Median RMSE by dataset",
                ["Original median RMSE", "External median RMSE"],
                "Median RMSE (USD)",
                "RMSE",
            ),
        ]
        for chart_column, (title, value_columns, axis_title, value_name) in zip(
            scale_columns, scale_specs
        ):
            scale_long = selected_display.melt(
                id_vars="model",
                value_vars=value_columns,
                var_name="Dataset",
                value_name=value_name,
            ).dropna(subset=[value_name])
            scale_long["Dataset"] = scale_long["Dataset"].str.replace(
                f" median {value_name}", "", regex=False
            )
            scale_fig = px.bar(
                scale_long,
                x="model",
                y=value_name,
                color="Dataset",
                barmode="group",
                text_auto=".4f",
                category_orders={"model": selected_models},
                color_discrete_sequence=[ACCENT_COLOR, SECONDARY_COLOR],
                title=title,
            )
            scale_fig.update_layout(xaxis_title=None, yaxis_title=axis_title)
            with chart_column:
                st.plotly_chart(
                    style_chart(scale_fig, 390),
                    width="stretch",
                    theme=None,
                    config={"displayModeBar": False},
                )

        xgb_original = display.loc[display["model"].eq("XGBoost"), "Original MAPE"]
        xgb_external = display.loc[display["model"].eq("XGBoost"), "External MAPE"]
        if not xgb_original.empty and not xgb_external.empty:
            st.warning(
                "XGBoost remains experimental: weighted MAPE increased from "
                f"{float(xgb_original.iloc[0]):.2f}% to "
                f"{float(xgb_external.iloc[0]):.2f}% on unseen assets."
            )

        st.info(
            "Naïve and ARIMA remain the top two models on unseen assets, but both "
            "record higher error. This supports limited generalisation, not a claim "
            "of guaranteed accuracy."
        )

        horizon_valid = comparable_metrics(external_comparison)
        horizon_valid = horizon_valid.loc[
            horizon_valid["model"].isin(selected_models)
        ].copy()
        horizon_rows: list[dict[str, Any]] = []
        for (horizon, model), group in horizon_valid.groupby(["horizon_days", "model"]):
            values = pd.to_numeric(group["mape"], errors="coerce")
            weights = pd.to_numeric(group["test_rows"], errors="coerce").fillna(0)
            mask = values.notna() & weights.gt(0)
            if mask.any():
                horizon_rows.append({
                    "Horizon": f"{int(horizon)}D",
                    "Model": str(model),
                    "MAPE": float(np.average(values[mask], weights=weights[mask])),
                    "horizon_order": int(horizon),
                })
        horizon_frame = pd.DataFrame(horizon_rows).sort_values("horizon_order")
        if not horizon_frame.empty:
            fig = px.line(
                horizon_frame,
                x="Horizon",
                y="MAPE",
                color="Model",
                markers=True,
                category_orders={"Model": selected_models},
                title="Selected-model error rises with the decision horizon",
            )
            fig.update_layout(xaxis_title="Forecast horizon", yaxis_title="MAPE (%)")
            st.plotly_chart(
                style_chart(fig, 430),
                width="stretch",
                theme=None,
                config={"displayModeBar": False},
            )

        st.caption(
            "Lower values are better. MAPE is prediction-weighted and is the primary "
            "cross-asset metric. MAE and RMSE are medians across comparable asset–horizon "
            "groups because coin prices use very different USD scales. Thirty-day paths "
            "remain high-uncertainty scenarios and are excluded from formal ranking."
        )

elif page == "Easy Mode":
    history, candle_error = fetch_candles(symbol, "1d", 365) if live_enabled else (pd.DataFrame(), "")
    if history.empty:
        history = fallback_history.tail(365)
    stats = indicators(history)
    decision = decision_score(stats, path, model_fresh, 30)
    score = float(decision["score"])
    action = str(decision["action"])
    today_move = float(live_row["change_24h"]) if live_row is not None and finite(live_row["change_24h"]) else stats.get("move_1", np.nan)
    month_move = stats.get("move_30", np.nan)
    future_move = (path["close"].iloc[-1] / anchor_price - 1) * 100 if not path.empty and anchor_price > 0 else np.nan
    st.markdown(f'<div class="terminal-head"><div class="live-line">EASY MODE · {html.escape(str(symbol).upper())}</div><div class="terminal-title">See the story, not the jargon</div><div class="terminal-sub">Today · last month · next 30-day scenario</div></div>', unsafe_allow_html=True)
    cards = st.columns(3)
    easy = [
        ("TODAY", f"{money(anchor_price)} · {pct(today_move)}", "Price is moving up today." if finite(today_move) and today_move > 0 else "Price is moving down today." if finite(today_move) else "Latest available market price."),
        ("LAST 30 DAYS", pct(month_move), "The coin gained value over the month." if finite(month_move) and month_move > 0 else "The coin lost value over the month." if finite(month_move) else "A one-month comparison."),
        ("NEXT 30 DAYS", pct(future_move), "The model path finishes higher." if finite(future_move) and future_move > 0 else "The model path finishes lower." if finite(future_move) else "Run the engine to create the path."),
    ]
    for column, (label, value, note) in zip(cards, easy):
        with column:
            st.markdown(f'<div class="easy-call"><div class="easy-label">{html.escape(label)}</div><div class="easy-value">{html.escape(value)}</div><div class="metric-note">{html.escape(note)}</div></div>', unsafe_allow_html=True)
    line = go.Figure()
    line.add_trace(go.Scatter(x=history["timestamp"], y=history["close"], name="What happened", line=dict(color=ACCENT_COLOR, width=2.2)))
    if not path.empty:
        line.add_trace(go.Scatter(x=path["date"], y=path["close"], name="What may happen", line=dict(color="#53657a", width=3), mode="lines+markers"))
    line.update_layout(title="Past movement and the next 30-day scenario", yaxis_title="USD")
    st.plotly_chart(style_chart(line, 520), width="stretch", theme=None, config={"displaylogo": False})
    action_tone = "up" if score >= 10 else "down" if score <= -10 else "warn"
    st.markdown(f'<div class="signal-core" style="min-height:220px"><div class="signal-content"><div class="signal-kicker">CURRENT MARKET SETUP</div><div class="signal-action {action_tone}">{html.escape(action)}</div><div class="signal-score">EVIDENCE {decision["evidence_strength"]:.0f}/100 · RISK {html.escape(str(decision["risk"]))}</div></div></div>', unsafe_allow_html=True)

st.markdown('<div class="fine-print">Forecasts are probabilistic scenarios, not guaranteed prices or personalised financial advice. No orders are placed by this dashboard.</div>', unsafe_allow_html=True)
