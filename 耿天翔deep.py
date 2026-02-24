"""
AEGIS QUANT Pro v5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
依赖安装:
  pip install streamlit ccxt pandas numpy plotly

启动:
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import random
from datetime import datetime, timedelta

# ── ccxt 软依赖 ───────────────────────────────────────────────────────────────
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  ─ 必须第一个 st 调用
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AEGIS QUANT | 投研终端",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS  ─ 白色简约风 + 移动端适配
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── 全局 ── */
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;color:#1F2937;}
.stApp{background:#FFFFFF;}
.block-container{padding:0 1.2rem 3rem!important;max-width:100%!important;}

/* ── 侧边栏 ── */
section[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid #E5E7EB;}
section[data-testid="stSidebar"] *{color:#374151;}
section[data-testid="stSidebar"] .stButton>button{
  background:#FFFFFF;border:1px solid #E5E7EB;color:#374151;
  border-radius:10px;font-size:13px;font-weight:500;
  text-align:left;padding:9px 14px;width:100%;transition:all .15s;
}
section[data-testid="stSidebar"] .stButton>button:hover{
  background:#EFF6FF;border-color:#BFDBFE;color:#1D4ED8;
}
[data-testid="collapsedControl"]{background:#FFFFFF!important;border-right:1px solid #E5E7EB;}

/* ── 通用组件 ── */
.stButton>button{border-radius:10px;font-weight:600;transition:all .18s;}
.stTextInput>div>div>input{border-radius:10px;border:1.5px solid #E5E7EB;background:#FFFFFF;font-family:'Inter',sans-serif;color:#1F2937;}
.stTextInput>div>div>input:focus{border-color:#3B82F6;box-shadow:0 0 0 3px rgba(59,130,246,.15);}
.stSelectbox>div>div{border-radius:10px;}
hr{border:none;border-top:1px solid #F3F4F6;margin:.5rem 0;}
[data-testid="stRadio"]>div{gap:6px;}
[data-testid="stRadio"]>div>label{font-size:13px;font-weight:500;}

/* ── 响应式：移动端堆叠 ── */
@media(max-width:768px){
  .block-container{padding:0 .6rem 2rem!important;}
  div[data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;}
  div[data-testid="stHorizontalBlock"]>div{min-width:100%!important;flex:1 1 100%!important;}
}
</style>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═════════════════════════════════════════════════════════════════════════════
_defaults = {
    "authenticated": False,
    "uid": "",
    "page": "🎯 核心策略",
    "cache_BTC_df": None,
    "cache_ETH_df": None,
    "cache_BTC_ticker": None,
    "cache_ETH_ticker": None,
    "cache_ts_BTC": 0.0,
    "cache_ts_ETH": 0.0,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# 超级 UID（后端隐藏，不在前端任何地方展示）
_VALID_UIDS = {"20061008", "88888888", "12345678", "66666666"}
DATA_TTL = 5  # 秒

# ═════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ═════════════════════════════════════════════════════════════════════════════
C = {
    "bg":       "#FFFFFF",
    "card":     "#F8FAFC",
    "border":   "#E5E7EB",
    "text":     "#1F2937",
    "sub":      "#6B7280",
    "blue":     "#2563EB",
    "blue_lt":  "#EFF6FF",
    "green":    "#059669",
    "green_lt": "#ECFDF5",
    "red":      "#DC2626",
    "red_lt":   "#FEF2F2",
    "amber":    "#D97706",
    "amber_lt": "#FFFBEB",
    "purple":   "#7C3AED",
    "mono":     "JetBrains Mono, monospace",
}
SHADOW = "0 2px 4px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.04)"
SHADOW_MD = "0 4px 12px rgba(0,0,0,.07)"

# ═════════════════════════════════════════════════════════════════════════════
# DATA ENGINE
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def _get_exchange():
    if not CCXT_AVAILABLE:
        return None
    for ExCls in [ccxt.okx, ccxt.binance]:
        try:
            ex = ExCls({"timeout": 8000, "enableRateLimit": True})
            return ex
        except Exception:
            pass
    return None

def _fetch_ohlcv(symbol_ccxt: str, tf: str = "1h", limit: int = 300):
    ex = _get_exchange()
    if ex is None:
        return None
    try:
        raw = ex.fetch_ohlcv(symbol_ccxt, timeframe=tf, limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("ts")
        return df
    except Exception:
        return None

def _fetch_ticker(symbol_ccxt: str):
    ex = _get_exchange()
    if ex is None:
        return None
    try:
        return ex.fetch_ticker(symbol_ccxt)
    except Exception:
        return None

# 时间周期 → ccxt timeframe 映射
_TF_MAP = {"15分钟": "15m", "1小时": "1h", "4小时": "4h"}
# 每个时间周期的种子偏移（保证各自独立）
_TF_SEED = {"15分钟": 0, "1小时": 100, "4小时": 200}

def _mock_ohlcv(symbol: str, tf_label: str, limit: int = 300) -> pd.DataFrame:
    """当 ccxt 不可用时生成高质量模拟数据，严格按 symbol + tf 隔离。"""
    seed_base = int(time.time() / DATA_TTL) * (1 if symbol == "BTC" else 3)
    seed = seed_base + _TF_SEED.get(tf_label, 0)
    rng  = np.random.default_rng(seed % (2**31))
    base = 104_800.0 if symbol == "BTC" else 3_942.0
    # 不同周期不同波动率
    vol_map = {"15分钟": 0.007, "1小时": 0.012, "4小时": 0.018}
    vol = vol_map.get(tf_label, 0.012)
    log_r  = rng.normal(0.00003, vol, limit)
    closes = base * np.exp(np.cumsum(log_r))
    spread = closes * rng.uniform(0.001, 0.006, limit)
    highs  = closes + spread
    lows   = closes - spread
    opens  = np.roll(closes, 1); opens[0] = closes[0]
    vols   = rng.lognormal(10 if symbol == "BTC" else 9, 0.4, limit)
    # 时间轴
    freq_map = {"15分钟": "15min", "1小时": "1h", "4小时": "4h"}
    freq = freq_map.get(tf_label, "1h")
    idx  = pd.date_range(end=datetime.utcnow(), periods=limit, freq=freq)
    return pd.DataFrame({"open": opens, "high": highs, "low": lows,
                          "close": closes, "volume": vols}, index=idx)

def get_ohlcv(symbol: str, tf_label: str = "1小时") -> pd.DataFrame:
    """获取 OHLCV，含 TTL 缓存，严格按 symbol 隔离。"""
    now    = time.time()
    ts_key = f"cache_ts_{symbol}"
    df_key = f"cache_{symbol}_df"
    cached = st.session_state[df_key]
    if cached is not None and now - st.session_state[ts_key] < DATA_TTL:
        return cached
    tf  = _TF_MAP.get(tf_label, "1h")
    sym = "BTC/USDT" if symbol == "BTC" else "ETH/USDT"
    df  = _fetch_ohlcv(sym, tf, 300)
    if df is None or df.empty:
        df = _mock_ohlcv(symbol, tf_label, 300)
    df = _calc_indicators(df)
    st.session_state[df_key] = df
    st.session_state[ts_key] = now
    return df

def get_ticker(symbol: str) -> dict:
    """获取实时 ticker，严格按 symbol 隔离。"""
    now    = time.time()
    tk_key = f"cache_{symbol}_ticker"
    ts_key = f"cache_ts_{symbol}"
    if st.session_state[tk_key] is not None and now - st.session_state[ts_key] < DATA_TTL:
        return st.session_state[tk_key]
    sym = "BTC/USDT" if symbol == "BTC" else "ETH/USDT"
    tk  = _fetch_ticker(sym)
    df  = st.session_state[f"cache_{symbol}_df"]
    if tk is None or not tk.get("last"):
        last = float(df.iloc[-1]["close"]) if df is not None else (104800.0 if symbol == "BTC" else 3942.0)
        prev = float(df.iloc[-2]["close"]) if df is not None and len(df) > 1 else last
        tk = {
            "last": last,
            "percentage": (last - prev) / prev * 100,
            "high": float(df["high"].iloc[-24:].max()) if df is not None else last * 1.02,
            "low":  float(df["low"].iloc[-24:].min())  if df is not None else last * 0.98,
            "quoteVolume": float(df["volume"].iloc[-24:].sum() * last) if df is not None else 0.0,
        }
    st.session_state[tk_key] = tk
    return tk

# ═════════════════════════════════════════════════════════════════════════════
# INDICATORS
# ═════════════════════════════════════════════════════════════════════════════

def _calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    for p in [9, 21, 55, 200]:
        df[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
    delta = c.diff()
    gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    df["rsi"]         = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12             = c.ewm(span=12, adjust=False).mean()
    ema26             = c.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]
    low9              = l.rolling(9, min_periods=1).min()
    high9             = h.rolling(9, min_periods=1).max()
    rsv               = (c - low9) / (high9 - low9 + 1e-12) * 100
    df["K"]           = rsv.ewm(com=2, adjust=False).mean()
    df["D"]           = df["K"].ewm(com=2, adjust=False).mean()
    df["J"]           = 3 * df["K"] - 2 * df["D"]
    ma20              = c.rolling(20).mean()
    std20             = c.rolling(20).std()
    df["bb_upper"]    = ma20 + 2 * std20
    df["bb_lower"]    = ma20 - 2 * std20
    df["bb_mid"]      = ma20
    prev_c            = c.shift(1)
    tr                = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]         = tr.rolling(14).mean()
    return df

def _score_strategy(df: pd.DataFrame) -> dict:
    """综合评分 + 策略计算，均线趋势决定方向，不会出现趋势空头却建议做多的错误。"""
    r    = df.iloc[-1]
    p    = float(r["close"])
    atr  = float(r["atr"]) if not np.isnan(r["atr"]) else p * 0.015
    sigs = []
    score = 0

    # RSI
    rsi = float(r["rsi"])
    if   rsi < 30:   sigs.append(("RSI(14)", f"{rsi:.1f}", "超卖",    "LONG",   2)); score += 2
    elif rsi < 45:   sigs.append(("RSI(14)", f"{rsi:.1f}", "偏弱",    "LONG",   1)); score += 1
    elif rsi > 75:   sigs.append(("RSI(14)", f"{rsi:.1f}", "极度超买", "SHORT", -2)); score -= 2
    elif rsi > 60:   sigs.append(("RSI(14)", f"{rsi:.1f}", "超买",    "SHORT", -1)); score -= 1
    else:            sigs.append(("RSI(14)", f"{rsi:.1f}", "中性",    "NEUT",   0))

    # MACD
    mv, ms, mh = float(r["macd"]), float(r["macd_signal"]), float(r["macd_hist"])
    if   mv > ms and mh > 0: sigs.append(("MACD", f"{mv:.0f}", "金叉↑", "LONG",   2)); score += 2
    elif mv < ms and mh < 0: sigs.append(("MACD", f"{mv:.0f}", "死叉↓", "SHORT", -2)); score -= 2
    else:                     sigs.append(("MACD", f"{mv:.0f}", "震荡",  "NEUT",   0))

    # KDJ
    K, D, J = float(r["K"]), float(r["D"]), float(r["J"])
    if   K > D and K < 80:  sigs.append(("KDJ-K", f"{K:.1f}", "金叉",  "LONG",   2)); score += 2
    elif K < D and K > 20:  sigs.append(("KDJ-K", f"{K:.1f}", "死叉",  "SHORT", -2)); score -= 2
    elif K > 85:             sigs.append(("KDJ-K", f"{K:.1f}", "超买",  "SHORT", -1)); score -= 1
    elif K < 15:             sigs.append(("KDJ-K", f"{K:.1f}", "超卖",  "LONG",   1)); score += 1
    else:                    sigs.append(("KDJ-K", f"{K:.1f}", "中性",  "NEUT",   0))

    # EMA 趋势 ── 这是方向的核心锚点
    e9, e21, e55 = float(r["ema9"]), float(r["ema21"]), float(r["ema55"])
    ema_bull = p > e9 > e21 > e55
    ema_bear = p < e9 < e21 < e55
    if   ema_bull: sigs.append(("EMA趋势", f"9>{e21:.0f}", "多头排列", "LONG",   3)); score += 3
    elif ema_bear: sigs.append(("EMA趋势", f"9<{e21:.0f}", "空头排列", "SHORT", -3)); score -= 3
    else:          sigs.append(("EMA趋势", "缠绕",          "震荡",    "NEUT",   0))

    # Bollinger Bands
    bb_u, bb_l = float(r["bb_upper"]), float(r["bb_lower"])
    if   p < bb_l: sigs.append(("BB",  f"下轨{bb_l:.0f}", "跌破下轨", "LONG",   1)); score += 1
    elif p > bb_u: sigs.append(("BB",  f"上轨{bb_u:.0f}", "突破上轨", "SHORT", -1)); score -= 1
    else:          sigs.append(("BB",  "通道内",           "中性",    "NEUT",   0))

    # ── 方向判断（EMA 趋势具有一票否决权）──────────────────────────────────
    # 如果 EMA 明确空头排列，最终方向不允许为做多
    if ema_bear and score > 0:
        score = -score // 2  # 强制转为偏空
    # 如果 EMA 明确多头排列，最终方向不允许为做空
    if ema_bull and score < 0:
        score = abs(score) // 2  # 强制转为偏多

    if   score >= 5:   direction, dtxt, col = "STRONG_LONG",  "🚀 强烈做多", C["green"]
    elif score >= 2:   direction, dtxt, col = "LONG",         "📈 轻多偏多", "#16A34A"
    elif score <= -5:  direction, dtxt, col = "STRONG_SHORT", "🔻 强烈做空", C["red"]
    elif score <= -2:  direction, dtxt, col = "SHORT",        "📉 轻空偏空", "#B91C1C"
    else:              direction, dtxt, col = "NEUTRAL",      "〰 震荡观望", C["amber"]

    # ── 点位计算 ─────────────────────────────────────────────────────────────
    if "LONG" in direction:
        entry  = p * 0.9990
        tp1    = entry + atr * 1.8
        tp2    = entry + atr * 3.5
        sl     = entry - atr * 1.2
    elif "SHORT" in direction:
        entry  = p * 1.0010
        tp1    = entry - atr * 1.8
        tp2    = entry - atr * 3.5
        sl     = entry + atr * 1.2
    else:
        entry  = p
        tp1    = p + atr * 1.5
        tp2    = p + atr * 3.0
        sl     = p - atr * 1.5

    rr      = abs(tp1 - entry) / max(abs(sl - entry), 1e-9)
    support = min(bb_l, e55) * 0.997
    resist  = max(bb_u, e21) * 1.003

    # ── 限价挂单策略 ─────────────────────────────────────────────────────────
    # 多单挂单：在支撑位下方买入，赢向阻力位
    limit_long_entry  = support * 0.998
    limit_long_tp1    = resist  * 0.998
    limit_long_tp2    = resist  * 1.012
    limit_long_sl     = support * 0.988
    limit_long_rr     = abs(limit_long_tp1 - limit_long_entry) / max(abs(limit_long_sl - limit_long_entry), 1e-9)
    # 空单挂单：在阻力位上方做空，打向支撑位
    limit_short_entry = resist  * 1.002
    limit_short_tp1   = support * 1.002
    limit_short_tp2   = support * 0.988
    limit_short_sl    = resist  * 1.012
    limit_short_rr    = abs(limit_short_tp1 - limit_short_entry) / max(abs(limit_short_sl - limit_short_entry), 1e-9)

    return dict(
        direction=direction, direction_text=dtxt, color=col,
        entry=entry, tp1=tp1, tp2=tp2, sl=sl, rr=rr, score=score,
        signals=sigs, support=support, resist=resist,
        rsi=rsi, K=K, D=D, J=J, macd=mv, macd_signal=ms, macd_hist=mh,
        price=p, atr=atr, ema9=e9, ema21=e21, ema55=e55, bb_upper=bb_u, bb_lower=bb_l,
        ema_bull=ema_bull, ema_bear=ema_bear,
        limit_long_entry=limit_long_entry, limit_long_tp1=limit_long_tp1,
        limit_long_tp2=limit_long_tp2, limit_long_sl=limit_long_sl, limit_long_rr=limit_long_rr,
        limit_short_entry=limit_short_entry, limit_short_tp1=limit_short_tp1,
        limit_short_tp2=limit_short_tp2, limit_short_sl=limit_short_sl, limit_short_rr=limit_short_rr,
    )

# ═════════════════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ═════════════════════════════════════════════════════════════════════════════

def _card(inner: str, extra_style: str = "") -> str:
    return (f'<div style="background:{C["card"]};border-radius:14px;padding:1.1rem 1.2rem;'
            f'box-shadow:{SHADOW};border:1px solid {C["border"]};{extra_style}">{inner}</div>')

def _white_card(inner: str, extra_style: str = "") -> str:
    return (f'<div style="background:{C["bg"]};border-radius:14px;padding:1.2rem 1.4rem;'
            f'box-shadow:{SHADOW_MD};border:1px solid {C["border"]};{extra_style}">{inner}</div>')

def _metric(label: str, value: str, sub: str = "", vc: str = C["text"], small: bool = False) -> str:
    vs = "18px" if small else "22px"
    return (f'<p style="margin:0;font-size:10px;font-weight:700;color:{C["sub"]};'
            f'letter-spacing:.6px;text-transform:uppercase">{label}</p>'
            f'<p style="margin:2px 0 0;font-size:{vs};font-weight:700;color:{vc};'
            f'font-family:{C["mono"]}">{value}</p>'
            + (f'<p style="margin:0;font-size:11px;color:{C["sub"]}">{sub}</p>' if sub else ""))

def _badge(stype: str) -> str:
    m = {
        "LONG":  (f"background:{C['green_lt']};color:{C['green']};border:1px solid #A7F3D0", "▲ 看多"),
        "SHORT": (f"background:{C['red_lt']};color:{C['red']};border:1px solid #FECACA",   "▼ 看空"),
        "NEUT":  (f"background:{C['amber_lt']};color:{C['amber']};border:1px solid #FDE68A","◆ 中性"),
    }
    cs, txt = m.get(stype, m["NEUT"])
    return f'<span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;{cs}">{txt}</span>'

def _dir_badge(txt: str, col: str) -> str:
    return (f'<span style="background:{col}18;color:{col};border:1.5px solid {col}44;'
            f'padding:6px 18px;border-radius:20px;font-size:13px;font-weight:800">{txt}</span>')

def fp(v: float, sym: str) -> str:
    return f"${v:,.1f}" if sym == "BTC" else f"${v:,.2f}"

def _section_header(title: str, sub: str = "") -> None:
    s = f'<p style="margin:0;font-size:18px;font-weight:800;color:{C["text"]};letter-spacing:-.3px">{title}</p>'
    if sub:
        s += f'<p style="margin:2px 0 0;font-size:13px;color:{C["sub"]}">{sub}</p>'
    st.markdown(s, unsafe_allow_html=True)
    st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)

def _spacer(h: str = ".8rem") -> None:
    st.markdown(f"<div style='height:{h}'></div>", unsafe_allow_html=True)

def _watermark() -> None:
    st.markdown(
        '<div style="text-align:center;margin-top:3rem;pointer-events:none;user-select:none">'
        f'<span style="font-size:10px;color:{C["sub"]};opacity:.2;letter-spacing:.5px">耿先生出品</span>'
        '</div>',
        unsafe_allow_html=True
    )

# ═════════════════════════════════════════════════════════════════════════════
# TOP STATUS BAR
# ═════════════════════════════════════════════════════════════════════════════

def _topbar() -> None:
    btc_tk  = get_ticker("BTC")
    eth_tk  = get_ticker("ETH")
    btc_p   = float(btc_tk.get("last", 0))
    eth_p   = float(eth_tk.get("last", 0))
    btc_pct = float(btc_tk.get("percentage", 0) or 0)
    eth_pct = float(eth_tk.get("percentage", 0) or 0)

    def _pc(v):  return f"{'▲' if v>=0 else '▼'} {abs(v):.2f}%"
    def _cc(v):  return C["green"] if v >= 0 else C["red"]

    mode    = "LIVE · ccxt" if CCXT_AVAILABLE else "DEMO"
    mbg     = C["green_lt"] if CCXT_AVAILABLE else C["amber_lt"]
    mtxt    = C["green"] if CCXT_AVAILABLE else C["amber"]

    st.markdown(
        f'<div style="background:{C["bg"]};border-bottom:1px solid {C["border"]};'
        f'padding:10px 20px;display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:10px;margin:-1rem -1.2rem 1.2rem">'
        f'<div style="display:flex;align-items:center;gap:10px">'
        f'<span style="font-size:15px;font-weight:800;color:{C["text"]};letter-spacing:-.3px">◈ AEGIS QUANT</span>'
        f'<span style="background:{mbg};color:{mtxt};padding:2px 9px;border-radius:6px;font-size:10px;font-weight:700">{mode}</span>'
        f'</div>'
        f'<div style="display:flex;gap:22px;align-items:center;flex-wrap:wrap">'
        f'<span style="font-size:12px;color:{C["sub"]}">₿ BTC/USDT&nbsp;'
        f'<span style="color:{C["text"]};font-weight:700;font-family:{C["mono"]}">${btc_p:,.1f}</span>&nbsp;'
        f'<span style="color:{_cc(btc_pct)};font-size:11px;font-weight:600">{_pc(btc_pct)}</span></span>'
        f'<span style="font-size:12px;color:{C["sub"]}">Ξ ETH/USDT&nbsp;'
        f'<span style="color:{C["text"]};font-weight:700;font-family:{C["mono"]}">${eth_p:,.2f}</span>&nbsp;'
        f'<span style="color:{_cc(eth_pct)};font-size:11px;font-weight:600">{_pc(eth_pct)}</span></span>'
        f'<span style="font-size:10px;color:{C["sub"]}">{datetime.now().strftime("%H:%M:%S")}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

def _sidebar() -> None:
    with st.sidebar:
        mask = st.session_state.uid[:4] + "****" if len(st.session_state.uid) >= 4 else st.session_state.uid
        st.markdown(
            f'<div style="background:{C["green_lt"]};border-radius:12px;padding:11px 15px;'
            f'margin-bottom:1.1rem;border:1px solid #A7F3D0">'
            f'<p style="margin:0;font-size:10px;font-weight:700;color:{C["green"]};letter-spacing:.5px">节点状态</p>'
            f'<p style="margin:4px 0 0;font-size:13px;font-weight:700;color:#065F46">✅ 节点: {mask}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("<hr>", unsafe_allow_html=True)
        NAV = [
            ("🎯", "核心策略",    "🎯 核心策略"),
            ("💰", "顶级返佣",    "💰 顶级返佣"),
            ("🔥", "清算热力图",  "🔥 清算热力图"),
            ("🌊", "链上监控",    "🌊 链上监控"),
            ("📰", "情绪分析",    "📰 情绪分析"),
            ("📞", "联系客服",    "📞 联系客服"),
        ]
        st.markdown(f'<p style="font-size:10px;font-weight:700;color:{C["sub"]};letter-spacing:.8px;margin-bottom:.3rem">导航</p>', unsafe_allow_html=True)
        for ico, label, key in NAV:
            active = st.session_state.page == key
            if active:
                st.markdown(
                    f'<div style="background:{C["blue_lt"]};border-radius:10px;padding:9px 14px;'
                    f'margin-bottom:4px;border:1px solid #BFDBFE">'
                    f'<span style="font-size:13px;font-weight:600;color:{C["blue"]}">{ico} {label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                if st.button(f"{ico} {label}", key=f"nav_{key}", use_container_width=True):
                    st.session_state.page = key
                    st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:10px;color:{C["sub"]};text-align:center">AEGIS QUANT Pro v5.0<br>TTL ≤ 5s</p>', unsafe_allow_html=True)
        _spacer(".3rem")
        if st.button("🚪 退出", use_container_width=True, key="logout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# GATE PAGE
# ═════════════════════════════════════════════════════════════════════════════

def render_gate() -> None:
    # 居中容器
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'padding:3.5rem 1rem 2rem;background:{C["bg"]}">'
        f'<div style="font-size:38px;font-weight:800;letter-spacing:-1.5px;color:{C["text"]};margin-bottom:4px">'
        f'AEGIS<span style="color:{C["blue"]}">QUANT</span></div>'
        f'<p style="font-size:13px;color:{C["sub"]};letter-spacing:1px;margin-bottom:2.5rem;text-align:center">'
        f'◈ PROFESSIONAL TRADING TERMINAL · 机构级量化投研平台</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    col_l, col_r = st.columns(2, gap="medium")

    with col_l:
        st.markdown(
            _white_card(
                f'<span style="display:inline-block;background:{C["green_lt"]};color:{C["green"]};'
                f'border:1px solid #A7F3D0;padding:3px 12px;border-radius:20px;font-size:11px;'
                f'font-weight:700;margin-bottom:1rem">🔑 节点授权模式 · 限时免费</span>'
                f'<p style="margin:0 0 .4rem;font-size:17px;font-weight:800;color:{C["text"]}">节点通道接入</p>'
                f'<p style="margin:0 0 .8rem;font-size:13px;color:{C["sub"]};line-height:1.7">'
                f'通过交易所 UID 绑定，即可<b>永久免费</b>使用全部核心功能。</p>'
                f'<div style="background:{C["blue_lt"]};border:1px solid #BFDBFE;border-radius:10px;'
                f'padding:8px 14px;font-size:12px;font-weight:700;color:{C["blue"]};margin-bottom:.9rem">'
                f'🏆 全网各大顶流交易所独家最高返佣 · 交易即挖矿</div>'
                f'<p style="margin:0;font-size:12px;color:{C["sub"]};line-height:1.6">'
                f'通过专属节点链接注册后，输入 UID 验证，系统自动激活全功能权限。</p>'
            ),
            unsafe_allow_html=True
        )
        _spacer(".5rem")
        uid_in = st.text_input(
            "节点 UID", placeholder="请输入您的 UID",
            key="uid_input", label_visibility="collapsed"
        )
        if st.button("🔓 验证 UID 并进入系统", use_container_width=True, key="btn_uid", type="primary"):
            if uid_in.strip() in _VALID_UIDS:
                st.session_state.authenticated = True
                st.session_state.uid = uid_in.strip()
                st.rerun()
            else:
                st.error("UID 未匹配，请确认已通过专属节点链接完成注册。")

    with col_r:
        st.markdown(
            _white_card(
                f'<span style="display:inline-block;background:{C["blue_lt"]};color:{C["blue"]};'
                f'border:1px solid #BFDBFE;padding:3px 12px;border-radius:20px;font-size:11px;'
                f'font-weight:700;margin-bottom:1rem">👑 Pro API · 独立买断</span>'
                f'<p style="margin:0 0 .4rem;font-size:17px;font-weight:800;color:{C["text"]}">Pro 独立授权</p>'
                f'<p style="margin:0 0 .8rem;font-size:13px;color:{C["sub"]};line-height:1.7">'
                f'无需绑定交易所，直接购买独立 API-Key，即时开通所有高级功能。</p>'
                f'<div style="background:{C["amber_lt"]};border:1px solid #FDE68A;border-radius:10px;'
                f'padding:8px 14px;font-size:12px;font-weight:700;color:{C["amber"]};margin-bottom:.9rem">'
                f'⚡ 50 USDT / 月 · 即时开通 · 私有数据流 · 优先支持</div>'
                f'<p style="margin:0;font-size:12px;color:{C["sub"]};line-height:1.6">'
                f'支持多子账户绑定，购买后享专属技术接入支持与私信通道。</p>'
            ),
            unsafe_allow_html=True
        )
        _spacer(".5rem")
        con_in = st.text_input(
            "Telegram / 微信", placeholder="@your_handle",
            key="con_input", label_visibility="collapsed"
        )
        if st.button("📩 提交 Pro 购买申请", use_container_width=True, key="btn_pro"):
            if con_in.strip():
                st.success(f"✅ 已收到申请，主理人将于 1 小时内联系：{con_in.strip()}")
            else:
                st.warning("请填写联系方式后再提交。")

    st.markdown(
        f'<p style="text-align:center;margin-top:1.5rem;font-size:11px;color:{C["sub"]};opacity:.7">'
        f'⚠️ 所有分析内容仅供参考，不构成投资建议。加密货币交易具有高风险，请自行评估。</p>',
        unsafe_allow_html=True
    )
    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1: 核心策略
# ═════════════════════════════════════════════════════════════════════════════

def _candle_fig(df: pd.DataFrame, sym: str) -> go.Figure:
    tail = df.tail(120).copy()
    xs   = list(range(len(tail)))
    fig  = go.Figure()
    fig.add_trace(go.Candlestick(
        x=xs, open=tail["open"], high=tail["high"], low=tail["low"], close=tail["close"],
        increasing=dict(fillcolor="#059669", line=dict(color="#047857", width=1)),
        decreasing=dict(fillcolor="#DC2626", line=dict(color="#B91C1C", width=1)),
        name=sym, showlegend=False,
        hoverlabel=dict(bgcolor="#1F2937", font=dict(color="#F9FAFB", size=11)),
    ))
    ema_cfg = [("ema9","#2563EB","EMA9"),("ema21","#D97706","EMA21"),("ema55","#7C3AED","EMA55")]
    for col, color, name in ema_cfg:
        fig.add_trace(go.Scatter(x=xs, y=tail[col], line=dict(color=color, width=1.5),
                                 name=name, mode="lines", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["bb_upper"],
                             line=dict(color="rgba(107,114,128,.3)", width=1, dash="dot"),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["bb_lower"],
                             line=dict(color="rgba(107,114,128,.3)", width=1, dash="dot"),
                             fill="tonexty", fillcolor="rgba(107,114,128,.04)",
                             showlegend=False, hoverinfo="skip"))
    step = 20
    tvs  = list(range(0, len(tail), step))
    tts  = [str(tail.index[i])[:13] for i in tvs]
    fig.update_layout(
        height=280, margin=dict(l=0, r=2, t=8, b=0),
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(showgrid=False, zeroline=False, rangeslider=dict(visible=False),
                   tickvals=tvs, ticktext=tts,
                   tickfont=dict(size=9, family="JetBrains Mono", color=C["sub"]),
                   fixedrange=False),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", zeroline=False, side="right",
                   tickfont=dict(size=9, family="JetBrains Mono", color=C["sub"]),
                   fixedrange=False),
        legend=dict(orientation="h", yanchor="top", y=1.06, xanchor="left", x=0,
                    font=dict(size=9, color=C["sub"]), bgcolor="rgba(0,0,0,0)"),
        dragmode="pan", font=dict(family="Inter"),
    )
    return fig

def _macd_fig(df: pd.DataFrame, sym_label: str) -> go.Figure:
    tail = df.tail(80)
    xs   = list(range(len(tail)))
    hc   = [C["green"] if v >= 0 else C["red"] for v in tail["macd_hist"]]
    fig  = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=tail["macd_hist"], marker_color=hc, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["macd"], line=dict(color=C["blue"], width=1.5), name="MACD"))
    fig.add_trace(go.Scatter(x=xs, y=tail["macd_signal"], line=dict(color=C["amber"], width=1.5), name="Signal"))
    fig.update_layout(
        title=dict(text=f"{sym_label} MACD", font=dict(size=11, color=C["sub"]), x=0),
        height=150, margin=dict(l=0, r=0, t=26, b=0),
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(showgrid=False, showticklabels=False, fixedrange=False),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6",
                   tickfont=dict(size=8, family="JetBrains Mono", color=C["sub"]), fixedrange=False),
        legend=dict(orientation="h", font=dict(size=9), y=1.2, bgcolor="rgba(0,0,0,0)"),
        dragmode="pan",
    )
    return fig

def _coin_block(sym: str, df: pd.DataFrame, s: dict, tk: dict, tf_label: str) -> None:
    dec  = 1 if sym == "BTC" else 2
    prc  = float(tk.get("last") or s["price"])
    pct  = float(tk.get("percentage") or 0)
    h24  = float(tk.get("high") or df["high"].iloc[-24:].max())
    l24  = float(tk.get("low")  or df["low"].iloc[-24:].min())
    vol  = float(tk.get("quoteVolume") or 0)
    pcc  = C["green"] if pct >= 0 else C["red"]
    pcs  = f"{'▲' if pct>=0 else '▼'} {abs(pct):.2f}%"

    # ── 币种标题栏 ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:{C["bg"]};border-radius:14px;padding:1rem 1.3rem;'
        f'box-shadow:{SHADOW};border:1px solid {C["border"]};margin-bottom:8px">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">'
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
        f'<span style="font-size:15px;font-weight:800;color:{C["text"]};font-family:{C["mono"]}">{sym}/USDT</span>'
        f'<span style="font-size:26px;font-weight:700;color:{C["text"]};font-family:{C["mono"]}">${prc:,.{dec}f}</span>'
        f'<span style="font-size:13px;font-weight:700;color:{pcc}">{pcs}</span>'
        f'<span style="font-size:11px;color:{C["sub"]}">H:${h24:,.{dec}f} | L:${l24:,.{dec}f} | Vol:${vol/1e6:.1f}M</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'{_dir_badge(s["direction_text"], s["color"])}'
        f'<span style="font-size:10px;color:{C["sub"]};background:{C["card"]};'
        f'padding:4px 10px;border-radius:8px;border:1px solid {C["border"]}">{tf_label}周期</span>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns([3, 2, 2], gap="small")

    # ── 图表 ────────────────────────────────────────────────────────────────
    with c1:
        fig = _candle_fig(df, sym)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": True,
                                "modeBarButtonsToRemove": ["toImage","lasso2d","select2d"],
                                "scrollZoom": True})

    # ── 指标矩阵 ─────────────────────────────────────────────────────────────
    with c2:
        srows = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;border-bottom:1px solid {C["border"]}">'
            f'<span style="font-size:11px;font-weight:600;color:{C["text"]}">{sg[0]}'
            f'<span style="color:{C["sub"]};font-weight:400;margin-left:4px;font-family:{C["mono"]};font-size:10px">{sg[1]}</span></span>'
            f'<span style="display:flex;align-items:center;gap:5px">'
            f'<span style="font-size:10px;color:{C["sub"]}">{sg[2]}</span>'
            f'{_badge(sg[3])}</span></div>'
            for sg in s["signals"]
        )
        buys  = sum(1 for sg in s["signals"] if sg[3] == "LONG")
        total = len(s["signals"])
        bw    = int(buys / total * 100)
        rc    = C["red"] if s["rsi"]>70 else C["green"] if s["rsi"]<30 else C["blue"]
        kc    = C["green"] if s["K"] > s["D"] else C["red"]
        inner = (
            f'<p style="margin:0 0 .5rem;font-size:10px;font-weight:700;color:{C["sub"]};'
            f'letter-spacing:.6px;text-transform:uppercase">指标信号矩阵</p>'
            f'{srows}'
            f'<div style="margin-top:.7rem">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
            f'<span style="font-size:10px;color:{C["green"]};font-weight:600">看多 {buys}/{total}</span>'
            f'<span style="font-size:10px;color:{C["red"]};font-weight:600">看空 {total-buys}/{total}</span></div>'
            f'<div style="height:4px;border-radius:2px;background:{C["red_lt"]};overflow:hidden">'
            f'<div style="height:100%;width:{bw}%;background:{C["green"]};border-radius:2px"></div></div></div>'
            f'<div style="margin-top:.7rem;display:grid;grid-template-columns:1fr 1fr;gap:6px">'
            f'<div style="background:{C["bg"]};border-radius:8px;padding:7px 9px;border:1px solid {C["border"]}">'
            f'<p style="margin:0;font-size:9px;color:{C["sub"]};font-weight:700">RSI(14)</p>'
            f'<p style="margin:1px 0 0;font-size:17px;font-weight:700;color:{rc};font-family:{C["mono"]}">{s["rsi"]:.1f}</p></div>'
            f'<div style="background:{C["bg"]};border-radius:8px;padding:7px 9px;border:1px solid {C["border"]}">'
            f'<p style="margin:0;font-size:9px;color:{C["sub"]};font-weight:700">KDJ-K</p>'
            f'<p style="margin:1px 0 0;font-size:17px;font-weight:700;color:{kc};font-family:{C["mono"]}">{s["K"]:.1f}</p></div>'
            f'<div style="background:{C["bg"]};border-radius:8px;padding:7px 9px;border:1px solid {C["border"]}">'
            f'<p style="margin:0;font-size:9px;color:{C["sub"]};font-weight:700">EMA9</p>'
            f'<p style="margin:1px 0 0;font-size:12px;font-weight:700;color:{C["text"]};font-family:{C["mono"]}">${s["ema9"]:,.{dec}f}</p></div>'
            f'<div style="background:{C["bg"]};border-radius:8px;padding:7px 9px;border:1px solid {C["border"]}">'
            f'<p style="margin:0;font-size:9px;color:{C["sub"]};font-weight:700">EMA55</p>'
            f'<p style="margin:1px 0 0;font-size:12px;font-weight:700;color:{C["text"]};font-family:{C["mono"]}">${s["ema55"]:,.{dec}f}</p></div>'
            f'</div>'
        )
        st.markdown(_card(inner, "padding:.9rem 1rem"), unsafe_allow_html=True)

    # ── 精准点位 + 限价挂单 ──────────────────────────────────────────────────
    with c3:
        def lvr(lbl, val, col, ico):
            return (f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:6px 10px;border-radius:8px;background:{col}0D;margin-bottom:5px">'
                    f'<span style="font-size:11px;font-weight:500;color:{C["sub"]}">{ico} {lbl}</span>'
                    f'<span style="font-size:13px;font-weight:700;color:{col};font-family:{C["mono"]}">${val:,.{dec}f}</span></div>')

        tt = "📈 多头" if s["ema_bull"] else "📉 空头" if s["ema_bear"] else "↔ 缠绕"
        market_inner = (
            f'<p style="margin:0 0 .5rem;font-size:10px;font-weight:700;color:{C["sub"]};'
            f'letter-spacing:.6px;text-transform:uppercase">市价单策略</p>'
            + lvr("参考入场", s["entry"], C["blue"],   "⟶")
            + lvr("止盈 TP1", s["tp1"],   C["green"],  "✦")
            + lvr("止盈 TP2", s["tp2"],   "#047857",   "✦✦")
            + lvr("严格止损", s["sl"],    C["red"],    "⊗")
            + f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-top:1px solid {C["border"]};margin-top:4px">'
            + f'<span style="font-size:10px;color:{C["sub"]}">均线趋势</span>'
            + f'<span style="font-size:11px;font-weight:700;color:{C["text"]}">{tt}</span></div>'
            + f'<div style="display:flex;justify-content:space-between;padding:3px 0">'
            + f'<span style="font-size:10px;color:{C["sub"]}">风险收益比</span>'
            + f'<span style="font-size:12px;font-weight:700;color:{C["text"]};font-family:{C["mono"]}">1:{s["rr"]:.2f}</span></div>'
        )
        st.markdown(_card(market_inner, "padding:.9rem 1rem;margin-bottom:8px"), unsafe_allow_html=True)

        # 限价挂单卡片
        limit_inner = (
            f'<p style="margin:0 0 .5rem;font-size:10px;font-weight:700;color:{C["purple"]};'
            f'letter-spacing:.6px;text-transform:uppercase">📌 限价挂单策略</p>'
            f'<p style="margin:0 0 .4rem;font-size:9px;font-weight:700;color:{C["green"]}">▲ 支撑位挂多</p>'
            + lvr("挂单价",  s["limit_long_entry"], C["green"],  "⟶")
            + lvr("止盈",    s["limit_long_tp1"],   "#047857",   "✦")
            + lvr("止损",    s["limit_long_sl"],    "#991B1B",   "⊗")
            + f'<p style="margin:.5rem 0 .4rem;font-size:9px;font-weight:700;color:{C["red"]}">▼ 阻力位挂空</p>'
            + lvr("挂单价",  s["limit_short_entry"],C["red"],    "⟶")
            + lvr("止盈",    s["limit_short_tp1"],  "#B91C1C",   "✦")
            + lvr("止损",    s["limit_short_sl"],   "#DC2626",   "⊗")
            + f'<div style="background:{C["amber_lt"]};border-radius:8px;padding:6px 9px;border-left:2px solid {C["amber"]};margin-top:6px">'
            + f'<p style="margin:0;font-size:9px;color:{C["amber"]};line-height:1.5">⚠️ 限价单在价格到达对应区域时触发，注意设置止损。</p></div>'
        )
        st.markdown(_card(limit_inner, f"padding:.9rem 1rem;border-left:2px solid {C['purple']}"), unsafe_allow_html=True)

def render_strategy() -> None:
    _section_header("🎯 核心策略 · 精准点位", "实时多指标融合分析 · 市价 + 限价双策略输出")

    # ── 时间周期选择 ─────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:11px;font-weight:700;color:{C["sub"]};letter-spacing:.5px;margin-bottom:4px">选择分析周期</p>',
        unsafe_allow_html=True
    )
    tf_label = st.radio(
        "分析周期", ["15分钟", "1小时", "4小时"],
        index=1, horizontal=True, key="tf_radio", label_visibility="collapsed"
    )
    _spacer(".5rem")

    # ── 严格独立抓取，变量名含币种 ─────────────────────────────────────────
    btc_df  = get_ohlcv("BTC", tf_label)
    eth_df  = get_ohlcv("ETH", tf_label)
    btc_tk  = get_ticker("BTC")
    eth_tk  = get_ticker("ETH")
    btc_str = _score_strategy(btc_df)
    eth_str = _score_strategy(eth_df)

    for sym, df, s, tk in [
        ("BTC", btc_df, btc_str, btc_tk),
        ("ETH", eth_df, eth_str, eth_tk),
    ]:
        _coin_block(sym, df, s, tk, tf_label)
        _spacer(".5rem")

    # ── MACD 对比图 ──────────────────────────────────────────────────────────
    st.markdown(f'<p style="font-size:11px;font-weight:700;color:{C["sub"]};letter-spacing:.5px;margin:.3rem 0 .4rem">MACD 实时对比</p>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2, gap="small")
    with mc1:
        st.plotly_chart(_macd_fig(btc_df, "BTC/USDT"), use_container_width=True, config={"displayModeBar": False})
    with mc2:
        st.plotly_chart(_macd_fig(eth_df, "ETH/USDT"), use_container_width=True, config={"displayModeBar": False})

    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2: 顶级返佣通道
# ═════════════════════════════════════════════════════════════════════════════

def render_rebate() -> None:
    _section_header("💰 顶级返佣通道", "全网最高独家返佣 · 交易即挖矿 · 不开返佣等于白送手续费")

    # ── 痛点算账模块 ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1E3A5F,#1E40AF);border-radius:16px;'
        f'padding:1.8rem 2rem;margin-bottom:1.2rem;border:1px solid #1E40AF">'
        f'<p style="margin:0 0 .2rem;font-size:11px;font-weight:700;color:#93C5FD;letter-spacing:.8px">📊 一笔账 · 你到底亏了多少手续费？</p>'
        f'<p style="margin:0 0 1.2rem;font-size:17px;font-weight:800;color:#F9FAFB">以 1,000U 本金 × 100 倍杠杆为例</p>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px">'
        f'<div style="background:rgba(255,255,255,.08);border-radius:12px;padding:.9rem 1.1rem;border:1px solid rgba(255,255,255,.1)">'
        f'<p style="margin:0;font-size:10px;color:#93C5FD;font-weight:700">名义本金</p>'
        f'<p style="margin:3px 0 0;font-size:22px;font-weight:800;color:#F9FAFB;font-family:{C["mono"]}">100,000 U</p>'
        f'<p style="margin:0;font-size:11px;color:#60A5FA">1,000U × 100 倍</p></div>'
        f'<div style="background:rgba(220,38,38,.15);border-radius:12px;padding:.9rem 1.1rem;border:1px solid rgba(220,38,38,.3)">'
        f'<p style="margin:0;font-size:10px;color:#FCA5A5;font-weight:700">单笔手续费（0.05% taker）</p>'
        f'<p style="margin:3px 0 0;font-size:22px;font-weight:800;color:#EF4444;font-family:{C["mono"]}">50 U</p>'
        f'<p style="margin:0;font-size:11px;color:#FCA5A5">开仓+平仓 合计 100U / 笔</p></div>'
        f'<div style="background:rgba(220,38,38,.15);border-radius:12px;padding:.9rem 1.1rem;border:1px solid rgba(220,38,38,.3)">'
        f'<p style="margin:0;font-size:10px;color:#FCA5A5;font-weight:700">日均 5 笔 · 月度总损耗</p>'
        f'<p style="margin:3px 0 0;font-size:22px;font-weight:800;color:#EF4444;font-family:{C["mono"]}">15,000 U</p>'
        f'<p style="margin:0;font-size:11px;color:#FCA5A5">100U × 5 × 30 天</p></div>'
        f'<div style="background:rgba(5,150,105,.2);border-radius:12px;padding:.9rem 1.1rem;border:1px solid rgba(5,150,105,.4)">'
        f'<p style="margin:0;font-size:10px;color:#6EE7B7;font-weight:700">开启全网最高返佣后每月白赚</p>'
        f'<p style="margin:3px 0 0;font-size:22px;font-weight:800;color:#10B981;font-family:{C["mono"]}">10,500 U</p>'
        f'<p style="margin:0;font-size:11px;color:#6EE7B7">15,000 × 70% = 纯返还！</p></div>'
        f'</div>'
        f'<div style="margin-top:1rem;background:rgba(251,191,36,.15);border-radius:10px;padding:10px 14px;border-left:3px solid #FBBF24">'
        f'<p style="margin:0;font-size:12px;font-weight:700;color:#FDE68A">⚡ 结论：不开返佣 = 每月白白送给交易所 10,500U！返佣是零成本被动收入，不领就是亏损。</p>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── 首推双雄 ─────────────────────────────────────────────────────────────
    st.markdown(f'<p style="font-size:13px;font-weight:700;color:{C["text"]};margin-bottom:.7rem">🥇 首推双雄 · 重点推荐</p>', unsafe_allow_html=True)

    TOP2 = [
        {
            "name": "深币 Deepcoin",
            "logo": "https://placehold.co/160x52/EFF6FF/2563EB?text=Deepcoin&font=inter",
            "tag": "合约首选",
            "color": C["blue"],
            "tag_bg": C["blue_lt"],
            "desc": "合约首选平台，流动性深度无敌，滑点极低；高返佣极速到账，透明可查，高频交易者利润神器。",
            "feature": "🏆 深度第一 · 即时结算",
            "link": "#",
        },
        {
            "name": "热币 Hotcoin",
            "logo": "https://placehold.co/160x52/FEF3C7/D97706?text=Hotcoin&font=inter",
            "tag": "新币首发",
            "color": C["amber"],
            "tag_bg": C["amber_lt"],
            "desc": "专注合约与新币首发，佣金日结到账，平台活动丰富，新手与老手均适合，成长速度行业最快。",
            "feature": "🔥 日结佣金 · 活动最多",
            "link": "#",
        },
    ]

    tc1, tc2 = st.columns(2, gap="medium")
    for col, plat in zip([tc1, tc2], TOP2):
        with col:
            st.markdown(
                f'<div style="background:{C["bg"]};border-radius:16px;border:2px solid {plat["color"]}33;'
                f'box-shadow:{SHADOW_MD};overflow:hidden">'
                f'<div style="background:{plat["tag_bg"]};padding:1rem 1.2rem .8rem;text-align:center;border-bottom:1px solid {plat["color"]}22">'
                f'<img src="{plat["logo"]}" style="height:44px;object-fit:contain;border-radius:8px;width:auto;max-width:160px"/>'
                f'<div style="margin-top:.5rem"><span style="background:{plat["color"]}22;color:{plat["color"]};'
                f'border:1px solid {plat["color"]}44;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700">{plat["tag"]}</span></div>'
                f'</div>'
                f'<div style="padding:1rem 1.2rem">'
                f'<p style="margin:0 0 .3rem;font-size:15px;font-weight:800;color:{C["text"]}">{plat["name"]}</p>'
                f'<p style="margin:0 0 .6rem;font-size:12px;color:{C["sub"]};line-height:1.6">{plat["desc"]}</p>'
                f'<div style="background:{plat["tag_bg"]};border-radius:8px;padding:6px 10px;'
                f'font-size:11px;font-weight:700;color:{plat["color"]};margin-bottom:.8rem">{plat["feature"]}</div>'
                f'<a href="{plat["link"]}" target="_blank" style="display:block;text-align:center;'
                f'background:{plat["color"]};color:#fff;border-radius:10px;padding:9px 0;'
                f'font-size:13px;font-weight:700;text-decoration:none">点击开启高额返佣</a>'
                f'</div></div>',
                unsafe_allow_html=True
            )

    _spacer(".9rem")

    # ── 其他推荐 ─────────────────────────────────────────────────────────────
    st.markdown(f'<p style="font-size:13px;font-weight:700;color:{C["text"]};margin-bottom:.7rem">其他精选平台</p>', unsafe_allow_html=True)

    OTHER3 = [
        {
            "name": "币赢 CoinW",
            "logo": "https://placehold.co/140x46/ECFDF5/059669?text=CoinW&font=inter",
            "tag": "全币种",
            "color": C["green"],
            "desc": "覆盖全球用户，合规稳定，返佣按日结算到账，多品种交易均可享受高返。",
            "link": "#",
        },
        {
            "name": "唯客 WEEX",
            "logo": "https://placehold.co/140x46/F3E8FF/7C3AED?text=WEEX&font=inter",
            "tag": "U本位合约",
            "color": C["purple"],
            "desc": "极速撮合引擎，专业合约玩家首选，深度好、手续费低、返佣稳定。",
            "link": "#",
        },
        {
            "name": "芝麻 Gate.io",
            "logo": "https://placehold.co/140x46/F8FAFC/374151?text=Gate.io&font=inter",
            "tag": "现货+合约",
            "color": "#374151",
            "desc": "上币数量最多的交易所之一，现货合约双线返佣，流动性充裕，品种丰富。",
            "link": "#",
        },
    ]

    oc1, oc2, oc3 = st.columns(3, gap="small")
    for col, plat in zip([oc1, oc2, oc3], OTHER3):
        with col:
            st.markdown(
                f'<div style="background:{C["bg"]};border-radius:14px;border:1.5px solid {C["border"]};'
                f'box-shadow:{SHADOW};overflow:hidden">'
                f'<div style="background:{C["card"]};padding:.8rem 1rem .6rem;text-align:center;border-bottom:1px solid {C["border"]}">'
                f'<img src="{plat["logo"]}" style="height:38px;object-fit:contain;border-radius:6px;width:auto;max-width:140px"/>'
                f'<div style="margin-top:.4rem"><span style="background:{plat["color"]}18;color:{plat["color"]};'
                f'border:1px solid {plat["color"]}33;padding:1px 9px;border-radius:20px;font-size:10px;font-weight:700">{plat["tag"]}</span></div>'
                f'</div>'
                f'<div style="padding:.8rem 1rem">'
                f'<p style="margin:0 0 .3rem;font-size:13px;font-weight:800;color:{C["text"]}">{plat["name"]}</p>'
                f'<p style="margin:0 0 .7rem;font-size:11px;color:{C["sub"]};line-height:1.5">{plat["desc"]}</p>'
                f'<a href="{plat["link"]}" target="_blank" style="display:block;text-align:center;'
                f'background:{plat["color"]};color:#fff;border-radius:9px;padding:7px 0;'
                f'font-size:12px;font-weight:700;text-decoration:none">点击开启高额返佣</a>'
                f'</div></div>',
                unsafe_allow_html=True
            )

    _spacer(".9rem")
    st.markdown(
        f'<div style="background:{C["amber_lt"]};border-radius:12px;padding:.9rem 1.3rem;'
        f'border:1px solid #FDE68A;text-align:center">'
        f'<p style="margin:0;font-size:13px;font-weight:700;color:{C["amber"]}">💡 其他交易平台高返（Binance / OKX / Bybit 等），请联系专属客服一对一开通</p>'
        f'<p style="margin:4px 0 0;font-size:12px;color:#92400E">Telegram: <b>@bocheng668</b> &nbsp;|&nbsp; 无中间商 · 即时开通 · 返佣透明</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3: 清算热力图
# ═════════════════════════════════════════════════════════════════════════════

def render_liquidation() -> None:
    _section_header("🔥 全网清算热力图", "聚合全网多空清算分布，定位关键爆仓价格磁吸区域（模拟数据）")

    for sym_label, skey, step in [("BTC/USDT","BTC",600),("ETH/USDT","ETH",24)]:
        cdf  = st.session_state.get(f"cache_{skey}_df")
        base = float(cdf.iloc[-1]["close"]) if cdf is not None else (104800 if skey=="BTC" else 3942)
        dec  = 0 if skey=="BTC" else 1
        np.random.seed(7 + (1 if skey=="BTC" else 2))
        lvls = np.arange(base * .87, base * 1.13, step)
        ll   = np.exp(-((lvls - base*.94)**2) / (base*.025)**2) * 500
        sl   = np.exp(-((lvls - base*1.06)**2) / (base*.025)**2) * 400
        for m in [.93, .97, 1.03, 1.07]:
            idx = int(np.argmin(np.abs(lvls - base * m)))
            ll[max(0,idx-1):idx+2] += np.random.uniform(150, 500)
            sl[max(0,idx-1):idx+2] += np.random.uniform(100, 400)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=-ll, y=lvls, orientation="h", marker_color="rgba(5,150,105,.6)", name="多单清算",
                             hovertemplate="价格$%{y:,.0f}<br>多单%{customdata:.0f}万U<extra></extra>", customdata=ll))
        fig.add_trace(go.Bar(x=sl,  y=lvls, orientation="h", marker_color="rgba(220,38,38,.6)",  name="空单清算",
                             hovertemplate="价格$%{y:,.0f}<br>空单%{customdata:.0f}万U<extra></extra>", customdata=sl))
        fig.add_hline(y=base, line=dict(color=C["blue"],width=2),
                      annotation_text=f"  当前${base:,.{dec}f}", annotation_font=dict(color=C["blue"],size=11))
        mi  = int(np.argmax(ll))
        msi = int(np.argmax(sl))
        fig.add_hline(y=lvls[mi],  line=dict(color=C["green"],width=1,dash="dot"), annotation_text="  多单爆仓极值↓", annotation_font=dict(color=C["green"],size=9))
        fig.add_hline(y=lvls[msi], line=dict(color=C["red"],  width=1,dash="dot"), annotation_text="  空单爆仓极值↑", annotation_font=dict(color=C["red"],  size=9))
        fig.update_layout(
            title=dict(text=f"{sym_label} 清算痛点分布", font=dict(size=13,color=C["text"])),
            height=380, barmode="overlay",
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
            xaxis=dict(title="清算量（万U）", showgrid=True, gridcolor="#F3F4F6", zeroline=True, zerolinecolor=C["border"]),
            yaxis=dict(title="价格 USDT", showgrid=True, gridcolor="#F3F4F6", tickfont=dict(family="JetBrains Mono",size=10,color=C["sub"])),
            legend=dict(orientation="h", y=1.04, font=dict(size=10)),
            margin=dict(l=0,r=0,t=44,b=0), font=dict(family="Inter", color=C["text"]),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        c1,c2,c3,c4 = st.columns(4, gap="small")
        with c1: st.markdown(_card(_metric("多单最大爆仓区",f"${lvls[mi]:,.{dec}f}","向下磁吸价位",C["green"])), unsafe_allow_html=True)
        with c2: st.markdown(_card(_metric("空单最大爆仓区",f"${lvls[msi]:,.{dec}f}","向上磁吸价位",C["red"])),   unsafe_allow_html=True)
        with c3: st.markdown(_card(_metric("多空爆仓量比",f"{ll.sum()/max(sl.sum(),1):.2f}","多>空偏多头",C["blue"])), unsafe_allow_html=True)
        with c4: st.markdown(_card(_metric("24H总清算规模",f"${(ll.sum()+sl.sum())/10:.0f}万U","双向合计",C["purple"])), unsafe_allow_html=True)
        _spacer()

    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4: 链上监控
# ═════════════════════════════════════════════════════════════════════════════

def render_onchain() -> None:
    _section_header("🌊 链上巨鲸 · 数据监控", "大额链上转账异动实时播报 + 交易所净流量")

    rng   = np.random.default_rng(int(time.time()/60))
    wals  = ["0x3a8d…f9e1","bc1q4…7k2p","0x7c1f…a3d9","bc1p9…m5x1","0xd4e2…b8f3"]
    exs   = ["Binance","OKX","Coinbase","冷钱包","Kraken"]
    coins = ["BTC","ETH","BTC","ETH","BTC"]
    dirs  = ["转入交易所 ⚠️","转出交易所 ✅","钱包间转移","转入交易所 ⚠️","转出交易所 ✅"]
    sents = ["利空","利好","中性","利空","利好"]
    sc    = [C["red"],C["green"],C["amber"],C["red"],C["green"]]
    amts  = rng.uniform(300,6000,5)
    tago  = rng.integers(1,59,5)
    prcs  = [104800,3942,104800,3942,104800]
    usdv  = amts * np.array(prcs)

    rows = "".join(
        f'<tr style="border-bottom:1px solid {C["border"]}">'
        f'<td style="padding:9px 8px;font-size:11px;color:{C["sub"]};font-family:{C["mono"]}">{tago[i]}min前</td>'
        f'<td style="padding:9px 8px"><span style="background:{"#DBEAFE" if coins[i]=="BTC" else "#EDE9FE"};color:{"#1D4ED8" if coins[i]=="BTC" else "#6D28D9"};padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">{coins[i]}</span></td>'
        f'<td style="padding:9px 8px;font-size:12px;font-weight:700;color:{C["text"]};font-family:{C["mono"]}">{amts[i]:,.0f} {coins[i]}</td>'
        f'<td style="padding:9px 8px;font-size:12px;color:{C["sub"]}">${usdv[i]/1e6:.1f}M</td>'
        f'<td style="padding:9px 8px;font-size:11px;color:{C["sub"]}">{wals[i]} → {exs[i]}</td>'
        f'<td style="padding:9px 8px;font-size:11px;color:{C["sub"]}">{dirs[i]}</td>'
        f'<td style="padding:9px 8px"><span style="background:{sc[i]}1A;color:{sc[i]};padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700">{sents[i]}</span></td>'
        f'</tr>'
        for i in range(5)
    )

    st.markdown(
        f'<div style="background:{C["bg"]};border-radius:14px;padding:1.2rem;'
        f'box-shadow:{SHADOW};border:1px solid {C["border"]};margin-bottom:1rem;overflow-x:auto">'
        f'<p style="margin:0 0 .7rem;font-size:10px;font-weight:700;color:{C["sub"]};letter-spacing:.6px">🐳 大额链上转账异动</p>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:2px solid {C["border"]}">'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">时间</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">币种</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">数量</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">价值</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">地址流向</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">类型</th>'
        f'<th style="padding:6px 8px;font-size:9px;color:{C["sub"]};text-align:left;font-weight:700">信号</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True
    )

    dates30 = [(datetime.now()-timedelta(days=29-i)).strftime("%m/%d") for i in range(30)]
    flows   = np.random.default_rng(42).normal(0,1200,30)
    flows[5]=-4000;flows[12]=3600;flows[20]=-2800;flows[27]=2600
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates30, y=flows,
                         marker_color=[C["green"] if v<0 else C["red"] for v in flows]))
    fig.add_hline(y=0, line=dict(color=C["border"], width=1))
    fig.update_layout(
        title=dict(text="BTC 交易所净流量（近30日，绿=净流出=利好）",font=dict(size=12,color=C["sub"])),
        height=200, paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(showgrid=False, tickfont=dict(size=9,color=C["sub"])),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", tickfont=dict(size=9,family="JetBrains Mono",color=C["sub"])),
        margin=dict(l=0,r=0,t=32,b=0), font=dict(family="Inter"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    c1,c2,c3,c4 = st.columns(4, gap="small")
    with c1: st.markdown(_card(_metric("活跃巨鲸钱包","1,247","过去24小时",C["blue"])), unsafe_allow_html=True)
    with c2: st.markdown(_card(_metric("交易所BTC净流出","−12,340 BTC","近7日累计",C["green"])), unsafe_allow_html=True)
    with c3: st.markdown(_card(_metric("长期持有者占比","73.4%","LTH Supply %",C["purple"])), unsafe_allow_html=True)
    with c4: st.markdown(_card(_metric("矿工持仓变化","+420 BTC","近24小时",C["amber"])), unsafe_allow_html=True)

    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5: 情绪分析
# ═════════════════════════════════════════════════════════════════════════════

def render_sentiment() -> None:
    _section_header("📰 消息面 · 情绪实时分析", "恐慌贪婪指数 · 宏观资讯 · 资金费率")

    fg    = random.randint(50,78)
    fglbl = "极度贪婪" if fg>75 else "贪婪" if fg>55 else "中性" if fg>45 else "恐慌"
    fgc   = C["green"] if fg>55 else C["amber"] if fg>45 else C["red"]

    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=fg,
        title={"text": f"恐慌贪婪指数 · {fglbl}", "font": {"size":13, "color":C["sub"]}},
        number={"font": {"size":44, "family":"JetBrains Mono", "color":fgc}},
        gauge={
            "axis": {"range":[0,100],"tickwidth":1,"tickcolor":C["border"]},
            "bar": {"color":fgc, "thickness":.28},
            "bgcolor": C["bg"], "borderwidth":0,
            "steps": [
                {"range":[0,25],  "color":"#FEE2E2"},
                {"range":[25,45], "color":"#FEF3C7"},
                {"range":[45,55], "color":"#F9FAFB"},
                {"range":[55,75], "color":"#D1FAE5"},
                {"range":[75,100],"color":"#A7F3D0"},
            ],
        },
    ))
    fig_g.update_layout(height=255, margin=dict(l=16,r=16,t=36,b=0),
                        paper_bgcolor=C["bg"], font=dict(family="Inter"))

    cg, cn = st.columns([1,2], gap="medium")
    with cg:
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            _card(_metric("当前指数",str(fg),fglbl,fgc) + _metric("昨日指数",str(fg-random.randint(-7,7)),"环比对比",C["sub"])),
            unsafe_allow_html=True
        )
    news = [
        ("🟢","利好",C["green"],"ETF 净流入再创新高","贝莱德 IBIT 单日净流入突破 6.2 亿美元，机构需求强劲。","3min","机构"),
        ("🔴","利空",C["red"],  "美联储鹰派表态压制风险资产","FOMC 委员暗示暂不降息，美元指数走强至 104.8。","19min","宏观"),
        ("🟢","利好",C["green"],"Strategy 再度增持 BTC","额外购入 2,138 枚 BTC，总持仓超 21.4 万枚。","43min","机构"),
        ("⚪","中性",C["amber"],"以太坊活跃地址回升","ETH 日活突破 55 万，L2 生态数据亮眼。","1h","链上"),
        ("🔴","利空",C["red"],  "SEC 对加密平台启动新调查","监管消息短期压制情绪，注意风控。","2h","监管"),
    ]
    nh = "".join(
        f'<div style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid {C["border"]};align-items:flex-start">'
        f'<span style="font-size:11px;font-weight:700;color:{bc};white-space:nowrap;margin-top:2px">{ico} {sent}</span>'
        f'<div style="flex:1">'
        f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px">'
        f'<p style="margin:0;font-size:12px;font-weight:700;color:{C["text"]}">{title}</p>'
        f'<span style="background:{C["card"]};color:{C["sub"]};padding:1px 7px;border-radius:5px;font-size:9px;font-weight:600">{tag}</span></div>'
        f'<p style="margin:0;font-size:11px;color:{C["sub"]};line-height:1.5">{desc}</p>'
        f'<p style="margin:2px 0 0;font-size:10px;color:{C["border"]}">{t}</p>'
        f'</div></div>'
        for ico, sent, bc, title, desc, t, tag in news
    )
    with cn:
        st.markdown(
            _white_card(f'<p style="margin:0 0 .5rem;font-size:10px;font-weight:700;color:{C["sub"]};letter-spacing:.6px">最新宏观资讯</p>{nh}'),
            unsafe_allow_html=True
        )

    _spacer()
    d7  = [(datetime.now()-timedelta(days=6-i)).strftime("%m/%d") for i in range(7)]
    fgh = [38,45,52,61,58,68,fg]
    ft  = go.Figure()
    ft.add_trace(go.Scatter(x=d7,y=fgh,fill="tozeroy",fillcolor="rgba(37,99,235,.06)",
                            line=dict(color=C["blue"],width=2),mode="lines+markers",
                            marker=dict(size=6,color=C["blue"])))
    ft.add_hrect(y0=75,y1=100,fillcolor="rgba(5,150,105,.05)",line_width=0,annotation_text="极度贪婪",annotation_font_size=9)
    ft.add_hrect(y0=0,y1=25,fillcolor="rgba(220,38,38,.05)",line_width=0,annotation_text="极度恐慌",annotation_font_size=9)
    ft.update_layout(
        title=dict(text="近7日恐慌贪婪指数",font=dict(size=12,color=C["sub"])),
        height=170, paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(showgrid=False,tickfont=dict(size=10,color=C["sub"])),
        yaxis=dict(range=[0,100],showgrid=True,gridcolor="#F3F4F6",tickfont=dict(size=9,color=C["sub"])),
        margin=dict(l=0,r=0,t=28,b=0), font=dict(family="Inter"),
    )
    st.plotly_chart(ft, use_container_width=True, config={"displayModeBar": False})

    c1,c2,c3,c4 = st.columns(4, gap="small")
    with c1: st.markdown(_card(_metric("BTC 融资费率",f"+{random.uniform(.005,.09):.3f}%","永续合约·8H",C["blue"])),   unsafe_allow_html=True)
    with c2: st.markdown(_card(_metric("ETH 融资费率",f"+{random.uniform(.002,.06):.3f}%","永续合约·8H",C["purple"])), unsafe_allow_html=True)
    with c3: st.markdown(_card(_metric("全网多空比",f"{random.uniform(1.1,1.8):.2f}","多头偏多>1.0",C["green"])),        unsafe_allow_html=True)
    with c4: st.markdown(_card(_metric("加密市值总量",f"${random.uniform(3.1,3.5):.2f}T","较昨日+1.2%",C["amber"])),   unsafe_allow_html=True)

    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 6: 联系客服
# ═════════════════════════════════════════════════════════════════════════════

def render_contact() -> None:
    _section_header("📞 联系客服", "专属主理人 · 一对一服务")

    st.markdown(
        f'<div style="max-width:540px;margin:0 auto">'
        f'<div style="background:{C["bg"]};border-radius:22px;padding:2.5rem 2rem;'
        f'box-shadow:{SHADOW_MD};text-align:center;border:1px solid {C["border"]}">'
        f'<div style="width:72px;height:72px;background:linear-gradient(135deg,{C["blue"]},{C["purple"]});'
        f'border-radius:20px;display:flex;align-items:center;justify-content:center;'
        f'font-size:32px;margin:0 auto 1.1rem">◈</div>'
        f'<h2 style="margin:0 0 .3rem;font-size:20px;font-weight:800;color:{C["text"]}">AEGIS QUANT 客服</h2>'
        f'<p style="margin:0 0 1.8rem;color:{C["sub"]};font-size:13px">专业量化策略 · 一对一服务 · 机构级风控指导</p>'
        f'<div style="background:{C["blue_lt"]};border-radius:14px;padding:1.3rem;border:1px solid #BFDBFE;margin-bottom:1.3rem">'
        f'<p style="margin:0 0 .3rem;font-size:10px;font-weight:700;color:{C["blue"]};letter-spacing:.5px">TELEGRAM 官方唯一联系</p>'
        f'<p style="margin:0;font-size:24px;font-weight:800;color:{C["text"]};font-family:{C["mono"]}">@bocheng668</p>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;text-align:left;margin-bottom:1.3rem">'
        f'<div style="background:{C["card"]};border-radius:12px;padding:.9rem;border:1px solid {C["border"]}">'
        f'<p style="margin:0 0 4px;font-size:10px;font-weight:700;color:{C["sub"]}">服务内容</p>'
        f'<p style="margin:0;font-size:12px;color:{C["text"]};line-height:1.7">✦ 实时策略播报<br>✦ 精准点位提示<br>✦ 风控仓位管理<br>✦ 宏观研判解读</p></div>'
        f'<div style="background:{C["card"]};border-radius:12px;padding:.9rem;border:1px solid {C["border"]}">'
        f'<p style="margin:0 0 4px;font-size:10px;font-weight:700;color:{C["sub"]}">合作模式</p>'
        f'<p style="margin:0;font-size:12px;color:{C["text"]};line-height:1.7">✦ 节点授权（免费）<br>✦ Pro API 50U/月<br>✦ 机构定制服务<br>✦ 高返通道开通</p></div>'
        f'</div>'
        f'<div style="background:{C["amber_lt"]};border-radius:10px;padding:.8rem 1rem;'
        f'border-left:3px solid {C["amber"]};text-align:left">'
        f'<p style="margin:0;font-size:11px;color:#92400E;line-height:1.6">'
        f'⚠️ 请认准唯一官方 Telegram：<b>@bocheng668</b>，谨防假冒账号诈骗。本平台不承诺任何投资收益，分析仅供参考。</p>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )
    _watermark()

# ═════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    if not st.session_state.authenticated:
        render_gate()
        return

    _sidebar()
    _topbar()

    page = st.session_state.page
    if   "核心策略" in page: render_strategy()
    elif "返佣"     in page: render_rebate()
    elif "清算"     in page: render_liquidation()
    elif "链上"     in page: render_onchain()
    elif "情绪"     in page: render_sentiment()
    elif "客服"     in page: render_contact()
    else:                    render_strategy()

    # 5 秒自动刷新
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
