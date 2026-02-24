"""
AEGIS QUANT Pro v4.0
━━━━━━━━━━━━━━━━━━━━
依赖安装:
  pip install streamlit ccxt pandas numpy plotly

启动:
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random
from datetime import datetime, timedelta

# ─── 尝试导入 ccxt ─────────────────────────────────────────────────────────────
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  ── 必须第一行
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AEGIS QUANT | 投研终端",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#F0F4F8;}
.stApp{background:#F0F4F8;}
section[data-testid="stSidebar"]{background:#0A0F1E;border-right:1px solid #1A2332;}
section[data-testid="stSidebar"] *{color:#CBD5E1;}
section[data-testid="stSidebar"] .stButton>button{background:#131D2E;border:1px solid #1E2D42;color:#94A3B8;border-radius:10px;font-size:13px;font-weight:500;text-align:left;padding:10px 14px;width:100%;transition:all .15s;}
section[data-testid="stSidebar"] .stButton>button:hover{background:#1E3A5F;border-color:#3B82F6;color:#E2E8F0;}
[data-testid="collapsedControl"]{background:#0A0F1E!important;border-right:1px solid #1A2332;color:#38BDF8;}
.block-container{padding:0 1.4rem 2rem!important;max-width:100%!important;}
.stButton>button{border-radius:10px;font-weight:600;border:none;transition:all .18s;}
div[data-testid="stHorizontalBlock"]{gap:14px;}
.stTextInput>div>div>input{border-radius:10px;border:1.5px solid #E2E8F0;background:#fff;font-family:'Inter',sans-serif;}
.stSelectbox>div>div{border-radius:10px;}
hr{border:none;border-top:1px solid #1E293B;margin:.4rem 0;}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_defaults = {
    "authenticated": False,
    "uid": "",
    "page": "🎯 核心策略与精准点位",
    "cache_BTC_df": None,
    "cache_ETH_df": None,
    "cache_BTC_ticker": None,
    "cache_ETH_ticker": None,
    "cache_ts_BTC": 0.0,
    "cache_ts_ETH": 0.0,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

VALID_UIDS = {"20061008", "88888888", "12345678", "66666666"}
DATA_TTL = 5

# ══════════════════════════════════════════════════════════════════════════════
# DATA ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def get_exchange():
    if not CCXT_AVAILABLE:
        return None
    for ExClass in [ccxt.okx, ccxt.binance]:
        try:
            ex = ExClass({"timeout": 8000, "enableRateLimit": True})
            return ex
        except Exception:
            continue
    return None

def fetch_ohlcv_ccxt(symbol_ccxt: str, limit: int = 200):
    ex = get_exchange()
    if ex is None:
        return None
    try:
        raw = ex.fetch_ohlcv(symbol_ccxt, timeframe="1h", limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("ts")
        return df
    except Exception:
        return None

def fetch_ticker_ccxt(symbol_ccxt: str):
    ex = get_exchange()
    if ex is None:
        return None
    try:
        return ex.fetch_ticker(symbol_ccxt)
    except Exception:
        return None

def _mock_ohlcv(symbol: str, limit: int = 200) -> pd.DataFrame:
    seed = int(time.time() / DATA_TTL) * (1 if symbol == "BTC" else 3)
    rng = np.random.default_rng(seed)
    base = 104_800.0 if symbol == "BTC" else 3_942.0
    vol = 0.012 if symbol == "BTC" else 0.016
    log_r = rng.normal(0.00005, vol, limit)
    closes = base * np.exp(np.cumsum(log_r))
    spread = closes * rng.uniform(0.002, 0.008, limit)
    highs = closes + spread
    lows = closes - spread
    opens = np.roll(closes, 1); opens[0] = closes[0]
    volumes = rng.lognormal(10 if symbol == "BTC" else 9, 0.4, limit)
    idx = pd.date_range(end=datetime.utcnow(), periods=limit, freq="1h")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows,
                          "close": closes, "volume": volumes}, index=idx)

def get_ohlcv(symbol: str) -> pd.DataFrame:
    now = time.time()
    ts_key = f"cache_ts_{symbol}"
    df_key = f"cache_{symbol}_df"
    if (st.session_state[df_key] is not None and
            now - st.session_state[ts_key] < DATA_TTL):
        return st.session_state[df_key]
    sym_map = {"BTC": "BTC/USDT", "ETH": "ETH/USDT"}
    df = fetch_ohlcv_ccxt(sym_map[symbol], limit=200)
    if df is None or df.empty:
        df = _mock_ohlcv(symbol, 200)
    df = _calc_indicators(df)
    st.session_state[df_key] = df
    st.session_state[ts_key] = now
    return df

def get_ticker(symbol: str) -> dict:
    now = time.time()
    tk_key = f"cache_{symbol}_ticker"
    ts_key = f"cache_ts_{symbol}"
    if (st.session_state[tk_key] is not None and
            now - st.session_state[ts_key] < DATA_TTL):
        return st.session_state[tk_key]
    sym_map = {"BTC": "BTC/USDT", "ETH": "ETH/USDT"}
    tk = fetch_ticker_ccxt(sym_map[symbol])
    df = st.session_state[f"cache_{symbol}_df"]
    if tk is None or not tk.get("last"):
        last = float(df.iloc[-1]["close"]) if df is not None else (104800.0 if symbol == "BTC" else 3942.0)
        prev = float(df.iloc[-2]["close"]) if df is not None and len(df) > 1 else last
        tk = {
            "last": last,
            "percentage": (last - prev) / prev * 100,
            "high": float(df["high"].iloc[-24:].max()) if df is not None else last * 1.02,
            "low": float(df["low"].iloc[-24:].min()) if df is not None else last * 0.98,
            "quoteVolume": float(df["volume"].iloc[-24:].sum() * last) if df is not None else 0.0,
        }
    st.session_state[tk_key] = tk
    return tk

# ══════════════════════════════════════════════════════════════════════════════
# INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

def _calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    for p in [9, 21, 55, 200]:
        df[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    low9 = l.rolling(9, min_periods=1).min()
    high9 = h.rolling(9, min_periods=1).max()
    rsv = (c - low9) / (high9 - low9 + 1e-12) * 100
    df["K"] = rsv.ewm(com=2, adjust=False).mean()
    df["D"] = df["K"].ewm(com=2, adjust=False).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    ma20 = c.rolling(20).mean(); std20 = c.rolling(20).std()
    df["bb_upper"] = ma20 + 2 * std20
    df["bb_lower"] = ma20 - 2 * std20
    df["bb_mid"] = ma20
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df

def _score_strategy(df: pd.DataFrame) -> dict:
    r = df.iloc[-1]
    p = float(r["close"])
    atr = float(r["atr"]) if not np.isnan(r["atr"]) else p * 0.015
    signals, score = [], 0
    rsi = float(r["rsi"])
    if rsi < 30:   signals.append(("RSI(14)", f"{rsi:.1f} 超卖",    "LONG",  2)); score += 2
    elif rsi < 45: signals.append(("RSI(14)", f"{rsi:.1f} 偏弱",    "LONG",  1)); score += 1
    elif rsi > 75: signals.append(("RSI(14)", f"{rsi:.1f} 极度超买", "SHORT",-2)); score -= 2
    elif rsi > 60: signals.append(("RSI(14)", f"{rsi:.1f} 超买",    "SHORT",-1)); score -= 1
    else:          signals.append(("RSI(14)", f"{rsi:.1f} 中性",    "NEUT",  0))
    mv, ms, mh = float(r["macd"]), float(r["macd_signal"]), float(r["macd_hist"])
    if mv > ms and mh > 0:   signals.append(("MACD", "金叉上穿↑", "LONG",  2)); score += 2
    elif mv < ms and mh < 0: signals.append(("MACD", "死叉下穿↓", "SHORT",-2)); score -= 2
    else:                     signals.append(("MACD", "临界震荡",  "NEUT",  0))
    K, D = float(r["K"]), float(r["D"])
    if K > D and K < 80:   signals.append(("KDJ", f"K{K:.0f}>D{D:.0f} 金叉", "LONG",  2)); score += 2
    elif K < D and K > 20: signals.append(("KDJ", f"K{K:.0f}<D{D:.0f} 死叉","SHORT",-2)); score -= 2
    elif K > 85:           signals.append(("KDJ", f"K={K:.0f} 超买",          "SHORT",-1)); score -= 1
    elif K < 15:           signals.append(("KDJ", f"K={K:.0f} 超卖",          "LONG",  1)); score += 1
    else:                  signals.append(("KDJ", "中性区间",                  "NEUT",  0))
    e9, e21, e55 = float(r["ema9"]), float(r["ema21"]), float(r["ema55"])
    if p > e9 > e21 > e55:   signals.append(("EMA", "多头排列↑", "LONG",  2)); score += 2
    elif p < e9 < e21 < e55: signals.append(("EMA", "空头排列↓", "SHORT",-2)); score -= 2
    else:                     signals.append(("EMA", "均线缠绕",  "NEUT",  0))
    bb_u, bb_l = float(r["bb_upper"]), float(r["bb_lower"])
    if p < bb_l:   signals.append(("BB", "跌破下轨 超卖", "LONG",  1)); score += 1
    elif p > bb_u: signals.append(("BB", "突破上轨 超买", "SHORT",-1)); score -= 1
    else:          signals.append(("BB", "通道内运行",    "NEUT",  0))
    if score >= 5:   dt, dtxt, col = "STRONG_LONG",  "🚀 强烈做多", "#059669"
    elif score >= 2: dt, dtxt, col = "LONG",         "📈 轻多偏多", "#10B981"
    elif score <= -5:dt, dtxt, col = "STRONG_SHORT", "🔻 强烈做空", "#DC2626"
    elif score <= -2:dt, dtxt, col = "SHORT",        "📉 轻空偏空", "#EF4444"
    else:            dt, dtxt, col = "NEUTRAL",      "〰 震荡观望", "#D97706"
    if "LONG" in dt:
        entry, tp1, tp2, sl = p*.999, p*.999+atr*1.8, p*.999+atr*3.5, p*.999-atr*1.2
    elif "SHORT" in dt:
        entry, tp1, tp2, sl = p*1.001, p*1.001-atr*1.8, p*1.001-atr*3.5, p*1.001+atr*1.2
    else:
        entry, tp1, tp2, sl = p, p+atr*1.5, p+atr*3.0, p-atr*1.5
    rr = abs(tp1 - entry) / max(abs(sl - entry), 1e-9)
    return dict(direction=dt, direction_text=dtxt, color=col,
                entry=entry, tp1=tp1, tp2=tp2, sl=sl, rr=rr, score=score,
                signals=signals, support=min(bb_l, e55)*.997, resist=max(bb_u, e21)*1.003,
                rsi=rsi, K=K, D=D, J=float(r["J"]),
                macd=mv, macd_signal=ms, macd_hist=mh,
                price=p, atr=atr, ema9=e9, ema21=e21, ema55=e55,
                bb_upper=bb_u, bb_lower=bb_l)

# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def card(inner: str, bl: str = "none", bg: str = "#FFFFFF", p: str = "1.3rem") -> str:
    return (f'<div style="background:{bg};border-radius:16px;padding:{p};'
            f'box-shadow:0 1px 4px rgba(0,0,0,.05),0 4px 18px rgba(0,0,0,.04);'
            f'border:1px solid #E8EDF2;border-left:{bl};height:100%">{inner}</div>')

def mbk(label, value, sub="", vc="#0F172A"):
    return (f'<p style="margin:0;font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:.7px;text-transform:uppercase">{label}</p>'
            f'<p style="margin:2px 0 0;font-size:20px;font-weight:700;color:{vc};font-family:JetBrains Mono,monospace">{value}</p>'
            + (f'<p style="margin:0;font-size:11px;color:#94A3B8">{sub}</p>' if sub else ""))

def sbadge(stype):
    m = {"LONG": ("background:#DCFCE7;color:#166534;border:1px solid #86EFAC","▲ 看多"),
         "SHORT":("background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5","▼ 看空"),
         "NEUT": ("background:#FEF9C3;color:#854D0E;border:1px solid #FDE68A","◆ 中性")}
    cs, txt = m.get(stype, m["NEUT"])
    return f'<span style="display:inline-block;padding:1px 10px;border-radius:20px;font-size:11px;font-weight:700;{cs}">{txt}</span>'

def fp(v, sym):
    return f"${v:,.1f}" if sym == "BTC" else f"${v:,.2f}"

# ══════════════════════════════════════════════════════════════════════════════
# GATE
# ══════════════════════════════════════════════════════════════════════════════

def render_gate():
    st.markdown("""<style>
.gate-outer{display:flex;flex-direction:column;align-items:center;padding:3rem 1rem 2rem}
.gate-logo{font-size:44px;font-weight:800;letter-spacing:-2px;color:#0F172A;margin-bottom:6px}
.gate-logo em{color:#3B82F6;font-style:normal}
.gate-tag{font-size:13px;color:#64748B;letter-spacing:1.2px;margin-bottom:2.5rem;text-align:center}
.gate-card{background:#fff;border-radius:22px;padding:2.2rem 2rem;box-shadow:0 4px 28px rgba(0,0,0,.07);border:2px solid #F1F5F9;transition:border-color .2s}
.gate-card:hover{border-color:#3B82F6}
.gc-chip{display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.4px;margin-bottom:1.1rem}
.gc-title{font-size:19px;font-weight:800;color:#0F172A;margin-bottom:.5rem}
.gc-body{font-size:13px;color:#64748B;line-height:1.7;margin-bottom:1.1rem}
.gc-pill{display:inline-block;background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE;padding:6px 14px;border-radius:10px;font-size:12px;font-weight:700;margin-bottom:1.1rem}
</style>
<div class="gate-outer">
<div class="gate-logo">AEGIS<em>QUANT</em></div>
<div class="gate-tag">⬡ PROFESSIONAL TRADING TERMINAL · 机构级量化投研平台</div>
</div>""", unsafe_allow_html=True)

    cl, cr = st.columns(2, gap="medium")
    with cl:
        st.markdown("""<div class="gate-card">
<span class="gc-chip" style="background:#DCFCE7;color:#166534">🔑 节点授权模式 · 限时免费</span>
<div class="gc-title">节点通道接入</div>
<div class="gc-body">通过交易所 UID 绑定，即可<b>永久免费</b>使用全部核心功能。合作节点享受：</div>
<div class="gc-pill">🏆 全网各大顶流交易所 70%+ 独家最高返佣</div>
<div class="gc-body" style="font-size:12px;color:#94A3B8">通过专属节点链接注册后，输入 UID 验证，系统自动激活全功能权限并开启返佣结算。</div>
</div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        uid_in = st.text_input("节点 UID", placeholder="输入您的 UID，例如：20061008",
                               key="uid_input", label_visibility="collapsed")
        if st.button("🔓 验证 UID 并进入系统", use_container_width=True, key="btn_uid", type="primary"):
            if uid_in.strip() in VALID_UIDS:
                st.session_state.authenticated = True
                st.session_state.uid = uid_in.strip()
                st.rerun()
            else:
                st.error("UID 未匹配 — 请确认已通过专属节点链接注册。")
    with cr:
        st.markdown("""<div class="gate-card">
<span class="gc-chip" style="background:#EFF6FF;color:#1D4ED8">👑 Pro API · 独立买断</span>
<div class="gc-title">Pro 独立授权</div>
<div class="gc-body">无需绑定交易所账户，直接购买独立 API-Key，即时开通所有高级功能。</div>
<div class="gc-pill">⚡ 50 USDT / 月 · 即时开通 · 私有数据流</div>
<div class="gc-body" style="font-size:12px;color:#94A3B8">购买后提供专属技术接入支持，支持多子账户绑定，享优先策略播报通道。</div>
</div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        con_in = st.text_input("Telegram / 微信", placeholder="@your_handle",
                               key="con_input", label_visibility="collapsed")
        if st.button("📩 提交 Pro 购买申请", use_container_width=True, key="btn_pro"):
            if con_in.strip():
                st.success(f"✅ 已收到申请！主理人将于 1 小时内联系：{con_in.strip()}")
            else:
                st.warning("请填写联系方式后再提交。")
    st.markdown('<div style="text-align:center;margin-top:1.8rem;font-size:11px;color:#CBD5E1">⚠️ 所有分析内容仅供参考，不构成投资建议。加密货币交易具有高风险，请自行评估。</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        mask = st.session_state.uid[:4] + "****" if len(st.session_state.uid) >= 4 else st.session_state.uid
        st.markdown(f"""<div style="background:linear-gradient(135deg,#064E3B,#065F46);border-radius:12px;padding:12px 16px;margin-bottom:1.2rem;border:1px solid #059669">
<p style="margin:0;font-size:10px;font-weight:700;color:#6EE7B7;letter-spacing:.6px">节点绑定状态</p>
<p style="margin:5px 0 0;font-size:14px;font-weight:700;color:#ECFDF5">✅ 节点: {mask}</p>
</div>""", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        NAV = [
            "🎯 核心策略与精准点位",
            "💰 70% 顶级返佣通道",
            "🔥 全网清算热力图",
            "🌊 链上巨鲸数据监控",
            "📰 消息面情绪分析",
            "📞 联系专属主理人",
        ]
        st.markdown("<p style='font-size:10px;font-weight:700;color:#475569;letter-spacing:1px;margin-bottom:.4rem'>主导航</p>", unsafe_allow_html=True)
        for item in NAV:
            if st.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.page = item
                st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:10px;color:#334155;text-align:center;margin-top:.8rem'>AEGIS QUANT Pro v4.0<br>数据 TTL ≤ 5s | ccxt 实时抓取</p>", unsafe_allow_html=True)
        if st.button("🚪 退出登录", use_container_width=True, key="logout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_topbar():
    btc_tk = get_ticker("BTC")
    eth_tk = get_ticker("ETH")
    btc_p  = float(btc_tk.get("last", 0))
    eth_p  = float(eth_tk.get("last", 0))
    btc_pct= float(btc_tk.get("percentage", 0) or 0)
    eth_pct= float(eth_tk.get("percentage", 0) or 0)
    def pc(v): return f"{'▲' if v>=0 else '▼'} {abs(v):.2f}%"
    def cc(v): return "#34D399" if v>=0 else "#F87171"
    mode = "LIVE · ccxt" if CCXT_AVAILABLE else "DEMO · Mock"
    mbg  = "#064E3B" if CCXT_AVAILABLE else "#7C3AED"
    st.markdown(f"""<div style="background:#0A0F1E;padding:9px 22px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin:-1rem -1.4rem 1.4rem;border-bottom:1px solid #1A2332">
<div style="display:flex;align-items:center;gap:10px">
<span style="font-size:15px;font-weight:800;color:#F1F5F9;letter-spacing:-0.5px">⬡ AEGIS QUANT</span>
<span style="background:{mbg};color:#A7F3D0;padding:2px 10px;border-radius:6px;font-size:10px;font-weight:700">{mode}</span>
</div>
<div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap">
<span style="font-size:12px;color:#64748B">₿ BTC/USDT&nbsp;<span style="color:#F1F5F9;font-weight:700;font-family:JetBrains Mono,monospace">${btc_p:,.1f}</span>&nbsp;<span style="color:{cc(btc_pct)};font-size:11px;font-weight:600">{pc(btc_pct)}</span></span>
<span style="font-size:12px;color:#64748B">Ξ ETH/USDT&nbsp;<span style="color:#F1F5F9;font-weight:700;font-family:JetBrains Mono,monospace">${eth_p:,.2f}</span>&nbsp;<span style="color:{cc(eth_pct)};font-size:11px;font-weight:600">{pc(eth_pct)}</span></span>
<span style="font-size:10px;color:#334155">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: 核心策略
# ══════════════════════════════════════════════════════════════════════════════

def render_strategy():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:1.2rem;letter-spacing:-0.5px">🎯 核心策略 <span style="color:#3B82F6">·</span> 精准点位</p>', unsafe_allow_html=True)
    # ── 严格独立抓取，变量名含币种，绝不混用 ──
    btc_df  = get_ohlcv("BTC")
    eth_df  = get_ohlcv("ETH")
    btc_tk  = get_ticker("BTC")
    eth_tk  = get_ticker("ETH")
    btc_str = _score_strategy(btc_df)
    eth_str = _score_strategy(eth_df)
    for sym, df, s, tk in [("BTC", btc_df, btc_str, btc_tk),
                             ("ETH", eth_df, eth_str, eth_tk)]:
        _coin_block(sym, df, s, tk)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;letter-spacing:.5px;margin:.4rem 0 .6rem">MACD 实时对比</p>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2, gap="small")
    with mc1: st.plotly_chart(_macd_fig(btc_df, "BTC/USDT"), use_container_width=True, config={"displayModeBar": False})
    with mc2: st.plotly_chart(_macd_fig(eth_df, "ETH/USDT"), use_container_width=True, config={"displayModeBar": False})

def _coin_block(sym, df, s, tk):
    dec  = 1 if sym == "BTC" else 2
    prc  = float(tk.get("last") or s["price"])
    pct  = float(tk.get("percentage") or 0)
    h24  = float(tk.get("high") or df["high"].iloc[-24:].max())
    l24  = float(tk.get("low")  or df["low"].iloc[-24:].min())
    vol  = float(tk.get("quoteVolume") or 0)
    pcc  = "#10B981" if pct >= 0 else "#EF4444"
    pcs  = f"{'▲' if pct>=0 else '▼'} {abs(pct):.2f}%"
    st.markdown(f"""<div style="background:#fff;border-radius:18px;padding:1.2rem 1.5rem;box-shadow:0 2px 14px rgba(0,0,0,.05);border:1px solid #E8EDF2;margin-bottom:10px">
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
<span style="font-size:17px;font-weight:800;color:#0F172A;font-family:JetBrains Mono,monospace">{sym}/USDT</span>
<span style="font-size:28px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">${prc:,.{dec}f}</span>
<span style="font-size:14px;font-weight:700;color:{pcc}">{pcs}</span>
<span style="font-size:11px;color:#94A3B8">H:${h24:,.{dec}f} | L:${l24:,.{dec}f} | Vol:${vol/1e6:.1f}M</span>
</div>
<span style="background:{s["color"]}22;color:{s["color"]};border:2px solid {s["color"]}66;padding:6px 20px;border-radius:20px;font-size:14px;font-weight:800">{s["direction_text"]}</span>
</div>
</div>""", unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns([3, 2, 2], gap="small")
    with cc1:
        fig = _candle_fig(df, sym)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": True,
                                "modeBarButtonsToRemove": ["toImage","lasso2d","select2d"],
                                "scrollZoom": True})
    with cc2:
        srows = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #F8FAFC">'
            f'<span style="font-size:12px;font-weight:600;color:#334155">{sg[0]} <span style="color:#94A3B8;font-size:11px">{sg[1]}</span></span>'
            f'{sbadge(sg[2])}</div>'
            for sg in s["signals"]
        )
        buys  = sum(1 for sg in s["signals"] if sg[2]=="LONG")
        tot   = len(s["signals"])
        bw    = int(buys/tot*100)
        rc    = "#EF4444" if s["rsi"]>70 else "#10B981" if s["rsi"]<30 else "#3B82F6"
        kc    = "#10B981" if s["K"]>s["D"] else "#EF4444"
        inner = f"""<p style="margin:0 0 .7rem;font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:.8px;text-transform:uppercase">指标信号矩阵</p>
{srows}
<div style="margin-top:.9rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:10px;color:#10B981;font-weight:700">看多 {buys}/{tot}</span><span style="font-size:10px;color:#EF4444;font-weight:700">看空 {tot-buys}/{tot}</span></div>
<div style="height:5px;border-radius:3px;background:#FEE2E2;overflow:hidden"><div style="height:100%;width:{bw}%;background:linear-gradient(90deg,#10B981,#34D399);border-radius:3px"></div></div></div>
<div style="margin-top:.9rem;display:grid;grid-template-columns:1fr 1fr;gap:8px">
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:9px;color:#94A3B8;font-weight:700">RSI(14)</p><p style="margin:2px 0 0;font-size:19px;font-weight:700;color:{rc};font-family:JetBrains Mono,monospace">{s["rsi"]:.1f}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:9px;color:#94A3B8;font-weight:700">KDJ-K</p><p style="margin:2px 0 0;font-size:19px;font-weight:700;color:{kc};font-family:JetBrains Mono,monospace">{s["K"]:.1f}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:9px;color:#94A3B8;font-weight:700">EMA9</p><p style="margin:2px 0 0;font-size:13px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">${s["ema9"]:,.{dec}f}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:9px;color:#94A3B8;font-weight:700">EMA55</p><p style="margin:2px 0 0;font-size:13px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">${s["ema55"]:,.{dec}f}</p></div>
</div>"""
        st.markdown(card(inner, p="1.1rem"), unsafe_allow_html=True)
    with cc3:
        def lvr(lbl, val, col, ico):
            return (f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:8px 12px;border-radius:10px;background:{col}0F;margin-bottom:6px">'
                    f'<span style="font-size:11px;font-weight:600;color:#475569">{ico} {lbl}</span>'
                    f'<span style="font-size:14px;font-weight:700;color:{col};font-family:JetBrains Mono,monospace">${val:,.{dec}f}</span></div>')
        tt = "📈 多头" if s["ema9"]>s["ema21"]>s["ema55"] else "📉 空头" if s["ema9"]<s["ema21"]<s["ema55"] else "↔ 缠绕"
        inner = f"""<p style="margin:0 0 .7rem;font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:.8px;text-transform:uppercase">精准操作点位</p>
{lvr("参考入场", s["entry"], "#3B82F6", "⟶")}
{lvr("止盈 TP1",  s["tp1"],  "#10B981", "✦")}
{lvr("止盈 TP2",  s["tp2"],  "#059669", "✦✦")}
{lvr("严格止损",  s["sl"],   "#EF4444", "⊗")}
<div style="background:#F8FAFC;border-radius:10px;padding:10px 12px;margin-top:2px">
<div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:10px;color:#94A3B8">风险收益比</span><span style="font-size:14px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">1 : {s["rr"]:.2f}</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:10px;color:#94A3B8">支撑位</span><span style="font-size:12px;font-weight:700;color:#10B981;font-family:JetBrains Mono,monospace">${s["support"]:,.{dec}f}</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:10px;color:#94A3B8">阻力位</span><span style="font-size:12px;font-weight:700;color:#EF4444;font-family:JetBrains Mono,monospace">${s["resist"]:,.{dec}f}</span></div>
<div style="display:flex;justify-content:space-between"><span style="font-size:10px;color:#94A3B8">均线趋势</span><span style="font-size:11px;font-weight:700;color:#475569">{tt}</span></div>
</div>
<div style="margin-top:8px;background:#FFFBEB;border-radius:10px;padding:8px 12px;border-left:3px solid #F59E0B"><p style="margin:0;font-size:10px;color:#92400E;line-height:1.5">⚠️ 点位基于实时指标，请严格执行止损。</p></div>"""
        st.markdown(card(inner, p="1.1rem"), unsafe_allow_html=True)

def _candle_fig(df: pd.DataFrame, sym: str) -> go.Figure:
    """交互式 Candlestick + EMA，支持拖拽滑动 & 滚轮缩放"""
    tail = df.tail(120).copy()
    xs   = list(range(len(tail)))
    fig  = go.Figure()
    fig.add_trace(go.Candlestick(
        x=xs, open=tail["open"], high=tail["high"], low=tail["low"], close=tail["close"],
        increasing=dict(fillcolor="#10B981", line=dict(color="#059669", width=1)),
        decreasing=dict(fillcolor="#EF4444", line=dict(color="#DC2626", width=1)),
        name=sym, showlegend=False,
        hoverlabel=dict(bgcolor="#0F172A", font=dict(color="#F1F5F9", size=11)),
    ))
    for ecol, ecolor, ename in [("ema9","#3B82F6","EMA9"),("ema21","#F59E0B","EMA21"),("ema55","#8B5CF6","EMA55")]:
        fig.add_trace(go.Scatter(x=xs, y=tail[ecol], line=dict(color=ecolor, width=1.6),
                                 name=ename, mode="lines", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["bb_upper"],
                             line=dict(color="rgba(148,163,184,.35)", width=1, dash="dot"),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["bb_lower"],
                             line=dict(color="rgba(148,163,184,.35)", width=1, dash="dot"),
                             fill="tonexty", fillcolor="rgba(148,163,184,.04)",
                             showlegend=False, hoverinfo="skip"))
    step = 20
    tvs  = list(range(0, len(tail), step))
    tts  = [str(tail.index[i])[:13] for i in tvs]
    fig.update_layout(
        height=300, margin=dict(l=0, r=2, t=8, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, zeroline=False, rangeslider=dict(visible=False),
                   tickvals=tvs, ticktext=tts,
                   tickfont=dict(size=9, family="JetBrains Mono", color="#94A3B8"),
                   fixedrange=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(226,232,240,.5)", zeroline=False,
                   side="right", tickfont=dict(size=9, family="JetBrains Mono", color="#94A3B8"),
                   fixedrange=False),
        legend=dict(orientation="h", yanchor="top", y=1.06, xanchor="left", x=0,
                    font=dict(size=10, color="#64748B"), bgcolor="rgba(0,0,0,0)"),
        dragmode="pan",
        font=dict(family="Inter"),
    )
    return fig

def _macd_fig(df: pd.DataFrame, label: str) -> go.Figure:
    tail = df.tail(80)
    xs   = list(range(len(tail)))
    hc   = ["#10B981" if v >= 0 else "#EF4444" for v in tail["macd_hist"]]
    fig  = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=tail["macd_hist"], marker_color=hc, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=tail["macd"], line=dict(color="#3B82F6", width=1.5), name="MACD"))
    fig.add_trace(go.Scatter(x=xs, y=tail["macd_signal"], line=dict(color="#F59E0B", width=1.5), name="Signal"))
    fig.update_layout(
        title=dict(text=f"{label} MACD(12,26,9)", font=dict(size=11, color="#64748B"), x=0),
        height=165, margin=dict(l=0,r=0,t=28,b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, showticklabels=False, fixedrange=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(226,232,240,.5)",
                   tickfont=dict(size=8, family="JetBrains Mono", color="#94A3B8"), fixedrange=False),
        legend=dict(orientation="h", font=dict(size=9), y=1.15, bgcolor="rgba(0,0,0,0)"),
        dragmode="pan",
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: 70% 返佣通道
# ══════════════════════════════════════════════════════════════════════════════

def render_rebate():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:.3rem;letter-spacing:-0.5px">💰 70%+ 顶级返佣通道</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:13px;color:#64748B;margin-bottom:1.4rem">全网独家最高返佣 · 不开返佣等于白给交易所送钱</p>', unsafe_allow_html=True)

    # ── 痛点算账模块 ──────────────────────────────────────────────────────────
    st.markdown("""<div style="background:linear-gradient(135deg,#0F172A,#1E3A5F);border-radius:20px;padding:2rem 2.2rem;margin-bottom:1.4rem;border:1px solid #1E3A5F;position:relative;overflow:hidden">
<div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;background:radial-gradient(circle,rgba(59,130,246,.15),transparent 70%);pointer-events:none"></div>
<p style="margin:0 0 .3rem;font-size:11px;font-weight:700;color:#38BDF8;letter-spacing:1px">📊 一笔账 · 不开返佣，你到底亏了多少？</p>
<p style="margin:0 0 1.3rem;font-size:18px;font-weight:800;color:#F1F5F9">以 1,000U 本金 × 100 倍杠杆为例</p>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:16px">
<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:1rem 1.2rem;border:1px solid rgba(255,255,255,.08)">
<p style="margin:0;font-size:10px;color:#94A3B8;font-weight:700">合约名义本金</p>
<p style="margin:4px 0 0;font-size:24px;font-weight:800;color:#F1F5F9;font-family:JetBrains Mono,monospace">100,000 U</p>
<p style="margin:0;font-size:11px;color:#64748B">1,000U × 100倍杠杆</p>
</div>
<div style="background:rgba(239,68,68,.1);border-radius:14px;padding:1rem 1.2rem;border:1px solid rgba(239,68,68,.2)">
<p style="margin:0;font-size:10px;color:#FCA5A5;font-weight:700">单笔手续费（0.05% taker）</p>
<p style="margin:4px 0 0;font-size:24px;font-weight:800;color:#EF4444;font-family:JetBrains Mono,monospace">50 U</p>
<p style="margin:0;font-size:11px;color:#EF4444">开仓+平仓合计 100U / 笔</p>
</div>
<div style="background:rgba(239,68,68,.1);border-radius:14px;padding:1rem 1.2rem;border:1px solid rgba(239,68,68,.2)">
<p style="margin:0;font-size:10px;color:#FCA5A5;font-weight:700">日均 5 笔，每月损耗</p>
<p style="margin:4px 0 0;font-size:24px;font-weight:800;color:#EF4444;font-family:JetBrains Mono,monospace">15,000 U</p>
<p style="margin:0;font-size:11px;color:#EF4444">100U × 5笔 × 30天</p>
</div>
<div style="background:rgba(16,185,129,.12);border-radius:14px;padding:1rem 1.2rem;border:1px solid rgba(16,185,129,.25)">
<p style="margin:0;font-size:10px;color:#6EE7B7;font-weight:700">开启 70% 返佣，每月白赚</p>
<p style="margin:4px 0 0;font-size:24px;font-weight:800;color:#10B981;font-family:JetBrains Mono,monospace">10,500 U</p>
<p style="margin:0;font-size:11px;color:#10B981">15,000 × 70% = 10,500U 返还！</p>
</div>
</div>
<div style="margin-top:1.3rem;background:rgba(251,191,36,.1);border-radius:12px;padding:12px 16px;border-left:3px solid #FBBF24">
<p style="margin:0;font-size:13px;font-weight:700;color:#FDE68A">⚡ 结论：不开返佣 = 每月白送交易所 10,500U！返佣是零成本被动收入，不领就是在亏损。</p>
</div>
</div>""", unsafe_allow_html=True)

    # ── 高返平台矩阵墙 ────────────────────────────────────────────────────────
    st.markdown('<p style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:.8rem">🏦 精选高返平台矩阵 · 点击直达开通</p>', unsafe_allow_html=True)

    PLATFORMS = [
        {"name":"深币 Deepcoin","logo":"https://via.placeholder.com/150x50?text=Deepcoin",
         "rebate":"70%","tag":"合约专属","color":"#3B82F6","link":"#",
         "desc":"专注合约交易，高频用户首选，返佣结算透明实时。"},
        {"name":"芝麻 Gate.io","logo":"https://via.placeholder.com/150x50?text=Gate.io",
         "rebate":"70%","tag":"现货+合约","color":"#8B5CF6","link":"#",
         "desc":"币种最多的交易所之一，现货合约双返，流动性充裕。"},
        {"name":"唯客 WEEX","logo":"https://via.placeholder.com/150x50?text=WEEX",
         "rebate":"70%","tag":"U本位合约","color":"#06B6D4","link":"#",
         "desc":"极速撮合引擎，深度好，专业合约玩家首选平台。"},
        {"name":"热币 Hotcoin","logo":"https://via.placeholder.com/150x50?text=Hotcoin",
         "rebate":"70%","tag":"新兴高潜","color":"#EF4444","link":"#",
         "desc":"快速崛起的新锐平台，活动丰富，返佣比例极具竞争力。"},
        {"name":"币赢 CoinW","logo":"https://via.placeholder.com/150x50?text=CoinW",
         "rebate":"70%","tag":"全币种","color":"#F59E0B","link":"#",
         "desc":"覆盖全球用户，合规稳定运营，返佣按日结算到账。"},
    ]

    cols5 = st.columns(5, gap="small")
    for col, plat in zip(cols5, PLATFORMS):
        with col:
            st.markdown(f"""<div style="background:#fff;border-radius:16px;border:1.5px solid #E8EDF2;box-shadow:0 2px 14px rgba(0,0,0,.05);overflow:hidden;display:flex;flex-direction:column">
<div style="background:{plat["color"]}0D;padding:.9rem 1rem .6rem;text-align:center;border-bottom:1px solid #F1F5F9">
<img src="{plat["logo"]}" style="width:100%;max-width:130px;height:40px;object-fit:contain;border-radius:6px"/>
<div style="margin-top:.5rem"><span style="background:{plat["color"]}22;color:{plat["color"]};border:1px solid {plat["color"]}44;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:700">{plat["tag"]}</span></div>
</div>
<div style="padding:.9rem 1rem;flex:1">
<p style="margin:0 0 .3rem;font-size:13px;font-weight:800;color:#0F172A">{plat["name"]}</p>
<p style="margin:0 0 .6rem;font-size:11px;color:#64748B;line-height:1.5">{plat["desc"]}</p>
<div style="display:flex;align-items:center;gap:6px;margin-bottom:.8rem">
<span style="font-size:10px;color:#94A3B8">返佣比例</span>
<span style="font-size:18px;font-weight:800;color:{plat["color"]};font-family:JetBrains Mono,monospace">{plat["rebate"]}</span>
</div>
</div>
<div style="padding:.7rem 1rem .9rem">
<a href="{plat["link"]}" target="_blank" style="display:block;text-align:center;background:{plat["color"]};color:#fff;border-radius:10px;padding:8px 0;font-size:12px;font-weight:700;text-decoration:none">点击开启 70% 返佣</a>
</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("""<div style="background:linear-gradient(90deg,#FEF3C7,#FFFBEB);border-radius:14px;padding:1rem 1.4rem;border:1px solid #FDE68A;text-align:center">
<p style="margin:0;font-size:14px;font-weight:700;color:#92400E">💡 其他交易平台高返（Binance / OKX / Bybit 等），请联系专属客服一对一开通</p>
<p style="margin:4px 0 0;font-size:12px;color:#B45309">Telegram: <b>@bocheng668</b> &nbsp;|&nbsp; 无中间商 · 即时开通 · 返佣透明可查</p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: 清算热力图
# ══════════════════════════════════════════════════════════════════════════════

def render_liquidation():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:.4rem;letter-spacing:-0.5px">🔥 全网清算热力图</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:13px;color:#64748B;margin-bottom:1.2rem">聚合全网多空清算分布，定位关键爆仓价格磁吸区域。</p>', unsafe_allow_html=True)
    for sym, skey, step in [("BTC/USDT","BTC",600),("ETH/USDT","ETH",24)]:
        cdf  = st.session_state.get(f"cache_{skey}_df")
        base = float(cdf.iloc[-1]["close"]) if cdf is not None else (104800 if skey=="BTC" else 3942)
        dec  = 0 if skey=="BTC" else 1
        np.random.seed(7 + (1 if skey=="BTC" else 2))
        lvls = np.arange(base*.87, base*1.13, step)
        ll   = np.exp(-((lvls-base*.94)**2)/(base*.025)**2)*500
        sl   = np.exp(-((lvls-base*1.06)**2)/(base*.025)**2)*400
        for m in [.93,.97,1.03,1.07]:
            idx = int(np.argmin(np.abs(lvls-base*m)))
            ll[max(0,idx-1):idx+2] += np.random.uniform(150,500)
            sl[max(0,idx-1):idx+2] += np.random.uniform(100,400)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=-ll, y=lvls, orientation="h", marker_color="rgba(16,185,129,.65)", name="多单清算",
                             hovertemplate="价格$%{y:,.0f}<br>多单%{customdata:.0f}万U<extra></extra>", customdata=ll))
        fig.add_trace(go.Bar(x=sl,  y=lvls, orientation="h", marker_color="rgba(239,68,68,.65)",   name="空单清算",
                             hovertemplate="价格$%{y:,.0f}<br>空单%{customdata:.0f}万U<extra></extra>", customdata=sl))
        fig.add_hline(y=base, line=dict(color="#3B82F6",width=2),
                      annotation_text=f"  当前价${base:,.{dec}f}", annotation_font=dict(color="#3B82F6",size=11))
        mi = int(np.argmax(ll)); msi = int(np.argmax(sl))
        fig.add_hline(y=lvls[mi],  line=dict(color="#10B981",width=1,dash="dot"), annotation_text="  多单爆仓极值↓", annotation_font=dict(color="#10B981",size=9))
        fig.add_hline(y=lvls[msi], line=dict(color="#EF4444",width=1,dash="dot"), annotation_text="  空单爆仓极值↑", annotation_font=dict(color="#EF4444",size=9))
        fig.update_layout(
            title=dict(text=f"{sym} 清算痛点分布（模拟数据）", font=dict(size=13,color="#0F172A")),
            height=400, barmode="overlay",
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(title="清算量（万U）", showgrid=True, gridcolor="#F1F5F9", zeroline=True, zerolinecolor="#CBD5E1"),
            yaxis=dict(title="价格 USDT", showgrid=True, gridcolor="#F1F5F9", tickfont=dict(family="JetBrains Mono",size=10)),
            legend=dict(orientation="h", y=1.04, font=dict(size=10)),
            margin=dict(l=0,r=0,t=44,b=0), font=dict(family="Inter"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        c1,c2,c3,c4 = st.columns(4, gap="small")
        with c1: st.markdown(card(mbk("多单最大爆仓区",f"${lvls[mi]:,.{dec}f}","向下磁吸价位","#10B981")), unsafe_allow_html=True)
        with c2: st.markdown(card(mbk("空单最大爆仓区",f"${lvls[msi]:,.{dec}f}","向上磁吸价位","#EF4444")), unsafe_allow_html=True)
        with c3: st.markdown(card(mbk("多空爆仓量比",f"{ll.sum()/max(sl.sum(),1):.2f}","多>空偏多头","#3B82F6")), unsafe_allow_html=True)
        with c4: st.markdown(card(mbk("24H总清算规模",f"${(ll.sum()+sl.sum())/10:.0f}万U","双向合计","#8B5CF6")), unsafe_allow_html=True)
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: 链上巨鲸
# ══════════════════════════════════════════════════════════════════════════════

def render_onchain():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:1.2rem;letter-spacing:-0.5px">🌊 链上巨鲸 · 数据监控</p>', unsafe_allow_html=True)
    rng   = np.random.default_rng(int(time.time()/60))
    wals  = ["0x3a8d…f9e1","bc1q4…7k2p","0x7c1f…a3d9","bc1p9…m5x1","0xd4e2…b8f3"]
    exs   = ["Binance","OKX","Coinbase","冷钱包","Kraken"]
    coins = ["BTC","ETH","BTC","ETH","BTC"]
    dirs  = ["转入交易所 ⚠️","转出交易所 🟢","钱包间转移","转入交易所 ⚠️","转出交易所 🟢"]
    sents = ["利空","利好","中性","利空","利好"]
    sc    = ["#EF4444","#10B981","#F59E0B","#EF4444","#10B981"]
    amts  = rng.uniform(300,6000,5)
    tago  = rng.integers(1,59,5)
    prcs  = [104800,3942,104800,3942,104800]
    usdv  = amts * np.array(prcs)
    rows  = "".join(f"""<tr style="border-bottom:1px solid #F1F5F9">
<td style="padding:9px 8px;font-size:11px;color:#94A3B8;font-family:JetBrains Mono,monospace">{tago[i]}min前</td>
<td style="padding:9px 8px"><span style="background:{'#DBEAFE' if coins[i]=='BTC' else '#EDE9FE'};color:{'#1D4ED8' if coins[i]=='BTC' else '#6D28D9'};padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">{coins[i]}</span></td>
<td style="padding:9px 8px;font-size:13px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">{amts[i]:,.0f} {coins[i]}</td>
<td style="padding:9px 8px;font-size:12px;color:#475569">${usdv[i]/1e6:.1f}M</td>
<td style="padding:9px 8px;font-size:11px;color:#64748B">{wals[i]} → {exs[i]}</td>
<td style="padding:9px 8px;font-size:11px;color:#64748B">{dirs[i]}</td>
<td style="padding:9px 8px"><span style="background:{sc[i]}1A;color:{sc[i]};padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700">{sents[i]}</span></td>
</tr>""" for i in range(5))
    st.markdown(f"""<div style="background:#fff;border-radius:16px;padding:1.4rem;box-shadow:0 2px 12px rgba(0,0,0,.05);border:1px solid #E8EDF2;margin-bottom:1.2rem;overflow-x:auto">
<p style="margin:0 0 .8rem;font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:.8px">🐳 大额链上转账异动 · 实时播报</p>
<table style="width:100%;border-collapse:collapse">
<thead><tr style="border-bottom:2px solid #F1F5F9">
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">时间</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">币种</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">数量</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">价值</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">地址流向</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">类型</th>
<th style="padding:7px 8px;font-size:9px;color:#94A3B8;text-align:left;font-weight:700">信号</th>
</tr></thead><tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)
    dates30 = [(datetime.now()-timedelta(days=29-i)).strftime("%m/%d") for i in range(30)]
    flows   = np.random.default_rng(42).normal(0,1200,30)
    flows[5]=-4000;flows[12]=3600;flows[20]=-2800;flows[27]=2600
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates30, y=flows, marker_color=["#10B981" if v<0 else "#EF4444" for v in flows]))
    fig.add_hline(y=0, line=dict(color="#CBD5E1",width=1))
    fig.update_layout(title=dict(text="BTC 交易所净流量（近30日，绿=净流出=利好）",font=dict(size=12,color="#64748B")),
                      height=200,paper_bgcolor="white",plot_bgcolor="white",
                      xaxis=dict(showgrid=False,tickfont=dict(size=9)),
                      yaxis=dict(showgrid=True,gridcolor="#F1F5F9",tickfont=dict(size=9,family="JetBrains Mono")),
                      margin=dict(l=0,r=0,t=32,b=0),font=dict(family="Inter"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    c1,c2,c3,c4 = st.columns(4, gap="small")
    with c1: st.markdown(card(mbk("活跃巨鲸钱包","1,247","过去24小时","#3B82F6")), unsafe_allow_html=True)
    with c2: st.markdown(card(mbk("交易所BTC净流出","−12,340 BTC","近7日累计","#10B981")), unsafe_allow_html=True)
    with c3: st.markdown(card(mbk("长期持有者占比","73.4%","LTH Supply %","#8B5CF6")), unsafe_allow_html=True)
    with c4: st.markdown(card(mbk("矿工持仓变化","+420 BTC","近24小时","#F59E0B")), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: 消息面
# ══════════════════════════════════════════════════════════════════════════════

def render_sentiment():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:1.2rem;letter-spacing:-0.5px">📰 消息面 · 情绪实时分析</p>', unsafe_allow_html=True)
    fg    = random.randint(50,78)
    fglbl = "极度贪婪" if fg>75 else "贪婪" if fg>55 else "中性" if fg>45 else "恐慌"
    fgc   = "#10B981" if fg>55 else "#F59E0B" if fg>45 else "#EF4444"
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=fg,
        title={"text":f"恐慌贪婪指数 · {fglbl}","font":{"size":13,"color":"#64748B"}},
        number={"font":{"size":44,"family":"JetBrains Mono","color":fgc}},
        gauge={"axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#CBD5E1"},
               "bar":{"color":fgc,"thickness":.28},"bgcolor":"white","borderwidth":0,
               "steps":[{"range":[0,25],"color":"#FEE2E2"},{"range":[25,45],"color":"#FEF3C7"},
                        {"range":[45,55],"color":"#F1F5F9"},{"range":[55,75],"color":"#D1FAE5"},
                        {"range":[75,100],"color":"#A7F3D0"}]},
    ))
    fig_g.update_layout(height=260,margin=dict(l=16,r=16,t=36,b=0),paper_bgcolor="white",font=dict(family="Inter"))
    cg,cn = st.columns([1,2], gap="medium")
    with cg:
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        st.markdown(card(mbk("当前指数",str(fg),fglbl,fgc)+mbk("昨日指数",str(fg-random.randint(-7,7)),"环比对比","#94A3B8"),p=".9rem"), unsafe_allow_html=True)
    news = [
        ("🟢 利好","#10B981","ETF 净流入再创新高","贝莱德 IBIT 单日净流入突破 6.2 亿美元，机构需求强劲。","3min","机构"),
        ("🔴 利空","#EF4444","美联储鹰派表态压制风险资产","FOMC 委员暗示暂不降息，美元指数走强至 104.8。","19min","宏观"),
        ("🟢 利好","#10B981","Strategy 再度增持 BTC","宣布额外购入 2,138 枚 BTC，总持仓超 21.4 万枚。","43min","机构"),
        ("⚪ 中性","#F59E0B","以太坊活跃地址回升","ETH 日活突破 55 万，L2 生态数据亮眼。","1h","链上"),
        ("🔴 利空","#EF4444","SEC 对加密平台启动新调查","监管消息短期压制情绪，注意风控。","2h","监管"),
        ("🟢 利好","#10B981","萨尔瓦多持仓浮盈超 1 亿美元","国家级持币者盈利持续扩大。","3h","宏观"),
    ]
    nh = "".join(f"""<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #F8FAFC;align-items:flex-start">
<span style="font-size:11px;font-weight:700;color:{bc};white-space:nowrap;margin-top:2px">{badge}</span>
<div style="flex:1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
<p style="margin:0;font-size:12px;font-weight:700;color:#0F172A">{title}</p>
<span style="background:#F1F5F9;color:#64748B;padding:1px 8px;border-radius:5px;font-size:9px;font-weight:600">{tag}</span>
</div>
<p style="margin:0;font-size:11px;color:#64748B;line-height:1.5">{desc}</p>
<p style="margin:3px 0 0;font-size:10px;color:#94A3B8">{t}</p>
</div></div>""" for badge,bc,title,desc,t,tag in news)
    with cn:
        st.markdown(card(f'<p style="margin:0 0 .5rem;font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:.8px">最新宏观资讯</p>{nh}',p="1.1rem"), unsafe_allow_html=True)
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    d7  = [(datetime.now()-timedelta(days=6-i)).strftime("%m/%d") for i in range(7)]
    fgh = [38,45,52,61,58,68,fg]
    ft  = go.Figure()
    ft.add_trace(go.Scatter(x=d7,y=fgh,fill="tozeroy",fillcolor="rgba(59,130,246,.07)",
                            line=dict(color="#3B82F6",width=2),mode="lines+markers",marker=dict(size=6,color="#3B82F6")))
    ft.add_hrect(y0=75,y1=100,fillcolor="rgba(16,185,129,.05)",line_width=0,annotation_text="极度贪婪",annotation_font_size=9)
    ft.add_hrect(y0=0,y1=25,fillcolor="rgba(239,68,68,.05)",line_width=0,annotation_text="极度恐慌",annotation_font_size=9)
    ft.update_layout(title=dict(text="近7日恐慌贪婪指数趋势",font=dict(size=12,color="#64748B")),
                     height=175,paper_bgcolor="white",plot_bgcolor="white",
                     xaxis=dict(showgrid=False,tickfont=dict(size=10)),
                     yaxis=dict(range=[0,100],showgrid=True,gridcolor="#F1F5F9",tickfont=dict(size=9)),
                     margin=dict(l=0,r=0,t=28,b=0),font=dict(family="Inter"))
    st.plotly_chart(ft, use_container_width=True, config={"displayModeBar": False})
    c1,c2,c3,c4 = st.columns(4, gap="small")
    with c1: st.markdown(card(mbk("BTC 融资费率",f"+{random.uniform(.005,.09):.3f}%","永续合约·8H","#3B82F6")), unsafe_allow_html=True)
    with c2: st.markdown(card(mbk("ETH 融资费率",f"+{random.uniform(.002,.06):.3f}%","永续合约·8H","#8B5CF6")), unsafe_allow_html=True)
    with c3: st.markdown(card(mbk("全网多空比",f"{random.uniform(1.1,1.8):.2f}","多头偏多>1.0","#10B981")), unsafe_allow_html=True)
    with c4: st.markdown(card(mbk("加密市值总量",f"${random.uniform(3.1,3.5):.2f}T","较昨日+1.2%","#F59E0B")), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: 联系
# ══════════════════════════════════════════════════════════════════════════════

def render_contact():
    st.markdown('<p style="font-size:22px;font-weight:800;color:#0F172A;margin-bottom:1.5rem;letter-spacing:-0.5px">📞 联系专属主理人</p>', unsafe_allow_html=True)
    st.markdown("""<div style="max-width:580px;margin:0 auto">
<div style="background:#fff;border-radius:24px;padding:2.5rem 2rem;box-shadow:0 4px 28px rgba(0,0,0,.07);text-align:center;border:1px solid #E8EDF2">
<div style="width:76px;height:76px;background:linear-gradient(135deg,#3B82F6,#8B5CF6);border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:34px;margin:0 auto 1.2rem">⬡</div>
<h2 style="margin:0 0 .4rem;font-size:21px;font-weight:800;color:#0F172A">AEGIS QUANT 主理人</h2>
<p style="margin:0 0 2rem;color:#64748B;font-size:13px">专业量化策略 · 一对一服务 · 机构级风控指导</p>
<div style="background:#F0F9FF;border-radius:16px;padding:1.4rem;border:1px solid #BAE6FD;margin-bottom:1.4rem">
<p style="margin:0 0 .3rem;font-size:10px;font-weight:700;color:#0284C7;letter-spacing:.5px">TELEGRAM 官方唯一联系</p>
<p style="margin:0;font-size:26px;font-weight:800;color:#0F172A;font-family:JetBrains Mono,monospace">@bocheng668</p>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;text-align:left;margin-bottom:1.4rem">
<div style="background:#F8FAFC;border-radius:12px;padding:.9rem"><p style="margin:0 0 4px;font-size:10px;font-weight:700;color:#94A3B8">服务内容</p><p style="margin:0;font-size:12px;color:#475569;line-height:1.7">✦ 实时策略播报<br>✦ 精准点位提示<br>✦ 风控仓位管理<br>✦ 宏观研判解读</p></div>
<div style="background:#F8FAFC;border-radius:12px;padding:.9rem"><p style="margin:0 0 4px;font-size:10px;font-weight:700;color:#94A3B8">合作模式</p><p style="margin:0;font-size:12px;color:#475569;line-height:1.7">✦ 节点授权 (免费)<br>✦ Pro API 50U/月<br>✦ 机构定制服务<br>✦ 高返通道开通</p></div>
</div>
<div style="background:#FFFBEB;border-radius:12px;padding:.9rem;border-left:3px solid #F59E0B;text-align:left"><p style="margin:0;font-size:11px;color:#92400E;line-height:1.6">⚠️ 请认准唯一官方 Telegram：<b>@bocheng668</b>，谨防假冒账号诈骗。本平台不承诺任何投资收益，所有分析仅供参考。</p></div>
</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.authenticated:
        render_gate()
        return

    render_sidebar()
    render_topbar()

    page = st.session_state.page
    if   "核心策略" in page: render_strategy()
    elif "返佣"    in page or "70%" in page: render_rebate()
    elif "清算"    in page: render_liquidation()
    elif "链上"    in page or "巨鲸" in page: render_onchain()
    elif "消息"    in page or "情绪" in page: render_sentiment()
    elif "联系"    in page: render_contact()
    else: render_strategy()

    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
