import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import random
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AEGIS QUANT | 投研终端",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html,body,[class*="css"]{font-family:'Inter',sans-serif;background:#F8FAFC;}
.stApp{background:#F8FAFC;}
section[data-testid="stSidebar"]{background:#0F172A;border-right:1px solid #1E293B;}
section[data-testid="stSidebar"] *{color:#E2E8F0;}
[data-testid="collapsedControl"]{display:flex;align-items:center;justify-content:center;background:#0F172A;border:none;color:#38BDF8;border-radius:0 8px 8px 0;width:28px;}
.block-container{padding:0 1.5rem 2rem 1.5rem;max-width:100%;}
h1,h2,h3,h4{font-family:'Inter',sans-serif;}
.stButton>button{border-radius:10px;font-weight:600;border:none;transition:all .2s;}
.stTextInput>div>div>input{border-radius:10px;border:1.5px solid #E2E8F0;font-family:'Inter',sans-serif;}
.stSelectbox>div>div{border-radius:10px;}
hr{border:none;border-top:1px solid #E2E8F0;margin:0.5rem 0;}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "uid" not in st.session_state:
    st.session_state.uid = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = ""
if "page" not in st.session_state:
    st.session_state.page = "核心策略"
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}
if "last_fetch" not in st.session_state:
    st.session_state.last_fetch = {}

VALID_UIDS = {"20061008", "88888888", "12345678"}

# ══════════════════════════════════════════════════════════════════════════════
# DATA ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def get_market_data(symbol="BTC", ttl=5):
    now = time.time()
    cache_key = symbol
    if cache_key in st.session_state.data_cache:
        if now - st.session_state.last_fetch.get(cache_key, 0) < ttl:
            return st.session_state.data_cache[cache_key]
    data = _generate_ohlcv(symbol)
    st.session_state.data_cache[cache_key] = data
    st.session_state.last_fetch[cache_key] = now
    return data

def _generate_ohlcv(symbol):
    np.random.seed(int(time.time() / 5) % 10000)
    n = 200
    base = 104800 if symbol == "BTC" else 3950
    drift = np.random.uniform(-0.0003, 0.0004)
    vol = 0.018 if symbol == "BTC" else 0.022
    log_returns = np.random.normal(drift, vol, n)
    prices = base * np.exp(np.cumsum(log_returns))
    high = prices * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = prices * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_ = np.roll(prices, 1)
    open_[0] = prices[0]
    volume = np.random.lognormal(12, 0.5, n) * (base / 100000)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": prices, "volume": volume})
    df = _calc_indicators(df)
    return df

def _calc_indicators(df):
    c = df["close"]
    # EMA
    for p in [9, 21, 55, 200]:
        df[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    # KDJ
    low_min = df["low"].rolling(9).min()
    high_max = df["high"].rolling(9).max()
    rsv = (c - low_min) / (high_max - low_min + 1e-9) * 100
    df["K"] = rsv.ewm(com=2, adjust=False).mean()
    df["D"] = df["K"].ewm(com=2, adjust=False).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    # Bollinger
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df["bb_upper"] = ma20 + 2 * std20
    df["bb_lower"] = ma20 - 2 * std20
    df["bb_mid"] = ma20
    # ATR
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - c.shift()).abs(),
        (df["low"] - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    # VWAP
    df["vwap"] = (c * df["volume"]).cumsum() / df["volume"].cumsum()
    return df

def score_signals(df):
    r = df.iloc[-1]
    p = r["close"]
    signals = []
    score = 0
    # RSI
    if r["rsi"] < 30: signals.append(("RSI", "超卖", "LONG", 2)); score += 2
    elif r["rsi"] < 45: signals.append(("RSI", "偏弱", "LONG", 1)); score += 1
    elif r["rsi"] > 70: signals.append(("RSI", "超买", "SHORT", -2)); score -= 2
    elif r["rsi"] > 55: signals.append(("RSI", "偏强", "SHORT", -1)); score -= 1
    else: signals.append(("RSI", "中性", "NEUT", 0))
    # MACD
    if r["macd"] > r["macd_signal"] and r["macd_hist"] > 0:
        signals.append(("MACD", "金叉↑", "LONG", 2)); score += 2
    elif r["macd"] < r["macd_signal"] and r["macd_hist"] < 0:
        signals.append(("MACD", "死叉↓", "SHORT", -2)); score -= 2
    else:
        signals.append(("MACD", "交叉", "NEUT", 0))
    # KDJ
    if r["K"] > r["D"] and r["K"] < 80: signals.append(("KDJ", "金叉", "LONG", 2)); score += 2
    elif r["K"] < r["D"] and r["K"] > 20: signals.append(("KDJ", "死叉", "SHORT", -2)); score -= 2
    elif r["K"] > 85: signals.append(("KDJ", "超买", "SHORT", -1)); score -= 1
    elif r["K"] < 15: signals.append(("KDJ", "超卖", "LONG", 1)); score += 1
    else: signals.append(("KDJ", "中性", "NEUT", 0))
    # EMA trend
    if p > r["ema9"] > r["ema21"] > r["ema55"]:
        signals.append(("EMA", "多头排列", "LONG", 2)); score += 2
    elif p < r["ema9"] < r["ema21"] < r["ema55"]:
        signals.append(("EMA", "空头排列", "SHORT", -2)); score -= 2
    else:
        signals.append(("EMA", "震荡", "NEUT", 0))
    # BB
    if p < r["bb_lower"]: signals.append(("BB", "跌破下轨", "LONG", 1)); score += 1
    elif p > r["bb_upper"]: signals.append(("BB", "突破上轨", "SHORT", -1)); score -= 1
    else: signals.append(("BB", "通道内", "NEUT", 0))
    return score, signals

def get_strategy(df, symbol):
    r = df.iloc[-1]
    p = r["close"]
    atr = r["atr"]
    score, signals = score_signals(df)
    if score >= 4:
        direction = "STRONG_LONG"
        direction_text = "🚀 强烈做多"
        color = "#10B981"
        entry = p * 0.9985
        tp1 = entry + atr * 1.5
        tp2 = entry + atr * 3.0
        sl = entry - atr * 1.2
    elif score <= -4:
        direction = "STRONG_SHORT"
        direction_text = "🔻 逢高沽空"
        color = "#EF4444"
        entry = p * 1.0015
        tp1 = entry - atr * 1.5
        tp2 = entry - atr * 3.0
        sl = entry + atr * 1.2
    elif score >= 2:
        direction = "LONG"
        direction_text = "📈 轻多试多"
        color = "#34D399"
        entry = p * 0.999
        tp1 = entry + atr * 1.2
        tp2 = entry + atr * 2.5
        sl = entry - atr * 1.0
    elif score <= -2:
        direction = "SHORT"
        direction_text = "📉 轻空试空"
        color = "#F87171"
        entry = p * 1.001
        tp1 = entry - atr * 1.2
        tp2 = entry - atr * 2.5
        sl = entry + atr * 1.0
    else:
        direction = "NEUTRAL"
        direction_text = "〰 震荡观望"
        color = "#F59E0B"
        entry = p
        tp1 = p + atr
        tp2 = p + atr * 2
        sl = p - atr
    rr = abs(tp1 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 1
    support = min(r["bb_lower"], r["ema55"]) * 0.998
    resist = max(r["bb_upper"], r["ema21"]) * 1.002
    return {
        "direction": direction, "direction_text": direction_text, "color": color,
        "entry": entry, "tp1": tp1, "tp2": tp2, "sl": sl,
        "rr": rr, "score": score, "signals": signals,
        "support": support, "resist": resist,
        "rsi": r["rsi"], "K": r["K"], "D": r["D"], "J": r["J"],
        "macd": r["macd"], "macd_signal": r["macd_signal"], "macd_hist": r["macd_hist"],
        "price": p, "atr": atr, "ema9": r["ema9"], "ema21": r["ema21"], "ema55": r["ema55"],
        "bb_upper": r["bb_upper"], "bb_lower": r["bb_lower"],
    }

# ══════════════════════════════════════════════════════════════════════════════
# HELPER COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def card(content_html, padding="1.4rem", border_left="none", bg="#FFFFFF"):
    shadow = "0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04)"
    style = f"background:{bg};border-radius:16px;padding:{padding};box-shadow:{shadow};border:1px solid #F1F5F9;border-left:{border_left};height:100%;"
    st.markdown(f'<div style="{style}">{content_html}</div>', unsafe_allow_html=True)

def metric_mini(label, value, sub="", color="#1E293B"):
    return f'<div style="margin-bottom:1.1rem"><p style="margin:0;font-size:11px;font-weight:600;color:#94A3B8;letter-spacing:.8px;text-transform:uppercase">{label}</p><p style="margin:2px 0 0;font-size:22px;font-weight:700;color:{color};font-family:JetBrains Mono,monospace;letter-spacing:-0.5px">{value}</p>{"<p style=margin:0;font-size:12px;color:#94A3B8>" + sub + "</p>" if sub else ""}</div>'

def signal_badge(text, btype):
    colors = {"LONG": ("bg:#D1FAE5;color:#065F46;border:1px solid #A7F3D0", "▲"),
               "SHORT": ("bg:#FEE2E2;color:#991B1B;border:1px solid #FECACA", "▼"),
               "NEUT": ("bg:#FEF9C3;color:#854D0E;border:1px solid #FDE68A", "◆")}
    cs, ico = colors.get(btype, colors["NEUT"])
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;{cs}">{ico} {text}</span>'

def fmt_price(p, sym):
    if sym == "BTC":
        return f"${p:,.1f}"
    return f"${p:,.2f}"

# ══════════════════════════════════════════════════════════════════════════════
# GATE PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_gate():
    st.markdown("""
<style>
.gate-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:90vh;padding:2rem}
.gate-logo{font-size:42px;font-weight:800;letter-spacing:-2px;color:#0F172A;margin-bottom:4px}
.gate-logo span{color:#3B82F6}
.gate-sub{font-size:14px;color:#64748B;letter-spacing:1px;margin-bottom:2.5rem}
.gate-cards{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;width:100%;max-width:720px}
.gate-card{background:#fff;border-radius:20px;padding:2rem;box-shadow:0 4px 24px rgba(0,0,0,.07);border:2px solid #F1F5F9;transition:border-color .2s}
.gate-card:hover{border-color:#3B82F6}
.gc-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px;margin-bottom:1rem}
.gc-title{font-size:18px;font-weight:700;color:#0F172A;margin-bottom:.5rem}
.gc-desc{font-size:13px;color:#64748B;line-height:1.6;margin-bottom:1.2rem}
.gc-highlight{font-size:12px;font-weight:600;color:#3B82F6;background:#EFF6FF;padding:6px 12px;border-radius:8px;margin-bottom:1rem;display:inline-block}
@media(max-width:600px){.gate-cards{grid-template-columns:1fr}}
</style>
<div class="gate-wrap">
<div class="gate-logo">AEGIS<span>QUANT</span></div>
<div class="gate-sub">⬡ PROFESSIONAL TRADING TERMINAL · 机构级量化投研平台</div>
</div>
""", unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1], gap="medium")

    with col_l:
        st.markdown("""
<div class="gate-card">
<span class="gc-badge" style="background:#DCFCE7;color:#166534">🔑 节点授权模式 · 限时免费</span>
<div class="gc-title">节点通道接入</div>
<div class="gc-desc">通过您的交易所 UID 绑定，即可永久免费使用全部核心功能。全网<b>最高比例返佣</b>，交易即挖矿。</div>
<div class="gc-highlight">💰 OKX 返佣高达 60% · Binance 返佣高达 45%</div>
<div class="gc-desc" style="font-size:12px;color:#94A3B8">注册专属节点链接后，输入您的 UID 即可激活。系统将自动验证绑定状态。</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        uid_input = st.text_input("输入节点 UID", placeholder="例如：20061008", key="uid_field", label_visibility="collapsed")
        if st.button("🔓 验证 UID 并进入系统", use_container_width=True, key="uid_btn"):
            if uid_input.strip() in VALID_UIDS:
                st.session_state.authenticated = True
                st.session_state.uid = uid_input.strip()
                st.session_state.auth_mode = "node"
                st.rerun()
            else:
                st.error("UID 未匹配，请确认已通过专属节点链接注册。")

    with col_r:
        st.markdown("""
<div class="gate-card">
<span class="gc-badge" style="background:#EFF6FF;color:#1D4ED8">👑 Pro API · 独立买断</span>
<div class="gc-title">Pro 独立授权</div>
<div class="gc-desc">无需绑定交易所，直接购买独立 API-Key。适合已有稳定通道的机构客户与高频交易者。</div>
<div class="gc-highlight">⚡ 50U / 月 · 包含私有数据流 + 优先支持</div>
<div class="gc-desc" style="font-size:12px;color:#94A3B8">购买后即时开通，支持多账户绑定，提供专属技术接入支持与私信通道。</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        contact_input = st.text_input("留下 Telegram 或微信", placeholder="@your_handle", key="contact_field", label_visibility="collapsed")
        if st.button("📩 提交 Pro 购买申请", use_container_width=True, key="pro_btn"):
            if contact_input.strip():
                st.success(f"✅ 已收到申请！专属主理人将在 1 小时内联系您：{contact_input}")
            else:
                st.warning("请留下联系方式，方便主理人联系您。")

    st.markdown("""
<div style="text-align:center;margin-top:2rem;font-size:12px;color:#CBD5E1">
⚠️ 本平台仅提供技术分析参考，不构成投资建议。市场有风险，操作请谨慎。
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        uid_short = st.session_state.uid[:4] + "****" if len(st.session_state.uid) >= 4 else st.session_state.uid
        st.markdown(f"""
<div style="background:#10B981;border-radius:10px;padding:10px 14px;margin-bottom:1.2rem">
<p style="margin:0;font-size:11px;font-weight:600;color:#D1FAE5;letter-spacing:.5px">节点状态</p>
<p style="margin:4px 0 0;font-size:14px;font-weight:700;color:#ECFDF5">✅ 节点: {uid_short}</p>
</div>
""", unsafe_allow_html=True)
        st.markdown("---")
        pages = [
            ("🎯", "核心策略与精准点位"),
            ("🔥", "全网清算热力图"),
            ("🌊", "链上巨鲸数据监控"),
            ("📰", "消息面情绪分析"),
            ("📞", "联系专属主理人"),
        ]
        st.markdown("<p style='font-size:11px;font-weight:600;color:#64748B;letter-spacing:1px;margin-bottom:.5rem'>主导航</p>", unsafe_allow_html=True)
        for icon, name in pages:
            active = st.session_state.page == name
            btn_style = "background:#3B82F6;color:#fff;border-radius:10px;" if active else "background:transparent;color:#CBD5E1;"
            if st.button(f"{icon} {name}", key=f"nav_{name}", use_container_width=True):
                st.session_state.page = name
                st.rerun()
        st.markdown("---")
        st.markdown("<p style='font-size:11px;color:#475569;text-align:center;margin-top:1rem'>AEGIS QUANT Pro v3.2.1<br>数据延迟 ≤ 5s</p>", unsafe_allow_html=True)
        if st.button("🚪 退出登录", use_container_width=True, key="logout"):
            st.session_state.authenticated = False
            st.session_state.uid = ""
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 核心策略
# ══════════════════════════════════════════════════════════════════════════════

def render_strategy():
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem">
<span style="font-size:28px;font-weight:800;color:#0F172A;letter-spacing:-1px">核心策略 <span style="color:#3B82F6">·</span> 精准点位</span>
<span style="background:#DBEAFE;color:#1D4ED8;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700">LIVE</span>
</div>
""", unsafe_allow_html=True)

    btc_df = get_market_data("BTC", ttl=5)
    eth_df = get_market_data("ETH", ttl=5)
    btc_s = get_strategy(btc_df, "BTC")
    eth_s = get_strategy(eth_df, "ETH")
    now_str = datetime.now().strftime("%H:%M:%S")

    for sym, s, df in [("BTC/USDT", btc_s, btc_df), ("ETH/USDT", eth_s, eth_df)]:
        short = sym.split("/")[0]
        price_str = fmt_price(s["price"], short)
        prev = df.iloc[-2]["close"]
        chg = (s["price"] - prev) / prev * 100
        chg_color = "#10B981" if chg >= 0 else "#EF4444"
        chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"

        st.markdown(f"""
<div style="background:#fff;border-radius:20px;padding:1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.05);border:1px solid #F1F5F9;margin-bottom:1.2rem">
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:1.2rem">
<div style="display:flex;align-items:center;gap:12px">
<span style="font-size:20px;font-weight:800;color:#0F172A;font-family:JetBrains Mono,monospace">{sym}</span>
<span style="font-size:26px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">{price_str}</span>
<span style="font-size:14px;font-weight:600;color:{chg_color}">{chg_str}</span>
</div>
<div style="display:flex;align-items:center;gap:10px">
<span style="background:{s["color"]}22;color:{s["color"]};border:1.5px solid {s["color"]}55;padding:6px 18px;border-radius:20px;font-size:14px;font-weight:700">{s["direction_text"]}</span>
<span style="font-size:11px;color:#94A3B8">更新 {now_str}</span>
</div>
</div>
</div>
""", unsafe_allow_html=True)

        # Columns: chart + indicators + levels
        c1, c2, c3 = st.columns([3, 2, 2], gap="small")

        with c1:
            fig = _make_price_chart(df, sym.split("/")[0], s)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with c2:
            # Indicators card
            def rsi_color(v):
                if v > 70: return "#EF4444"
                if v < 30: return "#10B981"
                return "#3B82F6"
            sigshtml = "".join([
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #F8FAFC">'
                f'<span style="font-size:12px;font-weight:600;color:#64748B">{sg[0]} <span style="color:#94A3B8;font-weight:400">{sg[1]}</span></span>'
                f'{signal_badge(sg[2], sg[2])}'
                f'</div>'
                for sg in s["signals"]
            ])
            total = len(s["signals"])
            buys = sum(1 for sg in s["signals"] if sg[2] == "LONG")
            sells = sum(1 for sg in s["signals"] if sg[2] == "SHORT")
            bar_buy = int(buys / total * 100)
            bar_sell = int(sells / total * 100)
            html = f"""
<p style="margin:0 0 .8rem;font-size:11px;font-weight:700;color:#94A3B8;letter-spacing:.8px;text-transform:uppercase">指标信号矩阵</p>
{sigshtml}
<div style="margin-top:1rem">
<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:11px;color:#10B981;font-weight:600">做多 {buys}/{total}</span><span style="font-size:11px;color:#EF4444;font-weight:600">做空 {sells}/{total}</span></div>
<div style="height:6px;border-radius:3px;background:#FEE2E2;overflow:hidden"><div style="height:100%;width:{bar_buy}%;background:linear-gradient(90deg,#10B981,#34D399);border-radius:3px"></div></div>
</div>
<div style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr;gap:8px">
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:10px;color:#94A3B8">RSI(14)</p><p style="margin:0;font-size:18px;font-weight:700;color:{rsi_color(s["rsi"])};font-family:JetBrains Mono,monospace">{s["rsi"]:.1f}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:10px;color:#94A3B8">KDJ-K</p><p style="margin:0;font-size:18px;font-weight:700;color:#3B82F6;font-family:JetBrains Mono,monospace">{s["K"]:.1f}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:10px;color:#94A3B8">EMA9</p><p style="margin:0;font-size:14px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">{fmt_price(s["ema9"], short)}</p></div>
<div style="background:#F8FAFC;border-radius:10px;padding:8px 10px"><p style="margin:0;font-size:10px;color:#94A3B8">EMA55</p><p style="margin:0;font-size:14px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">{fmt_price(s["ema55"], short)}</p></div>
</div>"""
            card(html, padding="1.2rem")

        with c3:
            is_long = "LONG" in s["direction"]
            is_short = "SHORT" in s["direction"]
            def lvl_row(label, val, color, icon=""):
                return f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:10px;background:{color}11;margin-bottom:6px"><span style="font-size:12px;font-weight:600;color:#475569">{icon} {label}</span><span style="font-size:15px;font-weight:700;color:{color};font-family:JetBrains Mono,monospace">{fmt_price(val, short)}</span></div>'
            html = f"""
<p style="margin:0 0 .8rem;font-size:11px;font-weight:700;color:#94A3B8;letter-spacing:.8px;text-transform:uppercase">精准操作点位</p>
{lvl_row("参考入场", s["entry"], "#3B82F6", "⟶")}
{lvl_row("止盈 TP1", s["tp1"], "#10B981", "✦")}
{lvl_row("止盈 TP2", s["tp2"], "#059669", "✦✦")}
{lvl_row("严格止损", s["sl"], "#EF4444", "⊗")}
<div style="margin-top:.8rem;background:#F8FAFC;border-radius:10px;padding:10px 12px">
<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:11px;color:#94A3B8">风险收益比</span><span style="font-size:14px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">1 : {s["rr"]:.2f}</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:11px;color:#94A3B8">支撑位</span><span style="font-size:13px;font-weight:600;color:#10B981;font-family:JetBrains Mono,monospace">{fmt_price(s["support"], short)}</span></div>
<div style="display:flex;justify-content:space-between"><span style="font-size:11px;color:#94A3B8">阻力位</span><span style="font-size:13px;font-weight:600;color:#EF4444;font-family:JetBrains Mono,monospace">{fmt_price(s["resist"], short)}</span></div>
</div>
<div style="margin-top:.8rem;background:#FFFBEB;border-radius:10px;padding:8px 12px;border-left:3px solid #F59E0B">
<p style="margin:0;font-size:11px;color:#92400E;line-height:1.5">⚠️ 本点位基于实时技术分析计算，结合自身仓位与风控严格执行止损。</p>
</div>"""
            card(html, padding="1.2rem")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # MACD Chart Row
    st.markdown("<p style='font-size:13px;font-weight:700;color:#64748B;letter-spacing:.5px;margin-bottom:.5rem'>MACD 实时图</p>", unsafe_allow_html=True)
    mc1, mc2 = st.columns(2, gap="small")
    with mc1:
        fig = _make_macd_chart(btc_df, "BTC")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with mc2:
        fig = _make_macd_chart(eth_df, "ETH")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def _make_price_chart(df, sym, s):
    tail = df.tail(80)
    fig = go.Figure()
    # Candles (simplified as line for clean look)
    fig.add_trace(go.Candlestick(
        x=list(range(len(tail))), open=tail["open"], high=tail["high"],
        low=tail["low"], close=tail["close"],
        increasing_fillcolor="#10B981", increasing_line_color="#10B981",
        decreasing_fillcolor="#EF4444", decreasing_line_color="#EF4444",
        name="Price", showlegend=False,
    ))
    colors = {"ema9": "#3B82F6", "ema21": "#F59E0B", "ema55": "#8B5CF6"}
    for ema, col in colors.items():
        fig.add_trace(go.Scatter(x=list(range(len(tail))), y=tail[ema], line=dict(color=col, width=1.2), name=ema.upper(), showlegend=True))
    # BB
    fig.add_trace(go.Scatter(x=list(range(len(tail))), y=tail["bb_upper"], line=dict(color="#E2E8F0", width=1, dash="dot"), name="BB Up", showlegend=False))
    fig.add_trace(go.Scatter(x=list(range(len(tail))), y=tail["bb_lower"], line=dict(color="#E2E8F0", width=1, dash="dot"), name="BB Low", fill="tonexty", fillcolor="rgba(148,163,184,.05)", showlegend=False))
    fig.update_layout(
        height=260, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, showticklabels=False, rangeslider_visible=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=9, family="JetBrains Mono"), side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1, font=dict(size=9)),
        font=dict(family="Inter"),
    )
    return fig

def _make_macd_chart(df, sym):
    tail = df.tail(60)
    fig = make_subplots(rows=1, cols=1)
    hist_colors = ["#10B981" if v >= 0 else "#EF4444" for v in tail["macd_hist"]]
    fig.add_trace(go.Bar(x=list(range(len(tail))), y=tail["macd_hist"], marker_color=hist_colors, name="Hist", showlegend=False))
    fig.add_trace(go.Scatter(x=list(range(len(tail))), y=tail["macd"], line=dict(color="#3B82F6", width=1.5), name="MACD"))
    fig.add_trace(go.Scatter(x=list(range(len(tail))), y=tail["macd_signal"], line=dict(color="#F59E0B", width=1.5), name="Signal"))
    fig.update_layout(
        title=dict(text=f"{sym} MACD", font=dict(size=12, color="#64748B"), x=0),
        height=160, margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=8, family="JetBrains Mono")),
        legend=dict(orientation="h", font=dict(size=9), y=1.15),
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 清算热力图
# ══════════════════════════════════════════════════════════════════════════════

def render_liquidation():
    st.markdown('<div style="font-size:24px;font-weight:800;color:#0F172A;margin-bottom:1.2rem">🔥 全网清算热力图</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748B;font-size:13px;margin-bottom:1.5rem">实时聚合全网多空双向清算数据，标注关键爆仓价格带，辅助研判价格磁吸区域。</p>', unsafe_allow_html=True)

    for sym, base, step in [("BTC/USDT", 104800, 800), ("ETH/USDT", 3950, 30)]:
        short = sym.split("/")[0]
        price_levels = np.arange(base * 0.88, base * 1.12, step)
        # Simulate long/short liquidation intensity
        np.random.seed(42)
        long_liq = np.exp(-((price_levels - base * 0.95) ** 2) / (base * 0.03) ** 2) * np.random.uniform(0.6, 1.0, len(price_levels)) * 500
        short_liq = np.exp(-((price_levels - base * 1.05) ** 2) / (base * 0.03) ** 2) * np.random.uniform(0.6, 1.0, len(price_levels)) * 400
        # Add some spikes
        for spike_pos in [0.93, 0.97, 1.03, 1.07]:
            idx = np.argmin(np.abs(price_levels - base * spike_pos))
            long_liq[idx - 2:idx + 2] += np.random.uniform(200, 600)
            short_liq[idx - 2:idx + 2] += np.random.uniform(150, 500)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=-long_liq, y=price_levels, orientation="h",
            marker_color="rgba(16,185,129,.7)", name="多单清算 (Long Liq)",
            hovertemplate="价格: $%{y:,.0f}<br>清算量: %{customdata:.0f}万U<extra></extra>",
            customdata=long_liq,
        ))
        fig.add_trace(go.Bar(
            x=short_liq, y=price_levels, orientation="h",
            marker_color="rgba(239,68,68,.7)", name="空单清算 (Short Liq)",
            hovertemplate="价格: $%{y:,.0f}<br>清算量: %{customdata:.0f}万U<extra></extra>",
            customdata=short_liq,
        ))
        # Current price line
        fig.add_hline(y=base, line=dict(color="#3B82F6", width=2, dash="solid"),
                      annotation_text=f"  当前价 ${base:,}", annotation_font=dict(color="#3B82F6", size=11))
        # Max pain lines
        max_long_idx = np.argmax(long_liq)
        max_short_idx = np.argmax(short_liq)
        fig.add_hline(y=price_levels[max_long_idx], line=dict(color="#10B981", width=1, dash="dot"),
                      annotation_text=f"  多单爆仓极值", annotation_font=dict(color="#10B981", size=9))
        fig.add_hline(y=price_levels[max_short_idx], line=dict(color="#EF4444", width=1, dash="dot"),
                      annotation_text=f"  空单爆仓极值", annotation_font=dict(color="#EF4444", size=9))
        fig.update_layout(
            title=dict(text=f"{sym} 清算热力图 (模拟数据)", font=dict(size=14, color="#0F172A")),
            height=400, barmode="overlay",
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(title="清算量 (万U)", showgrid=True, gridcolor="#F1F5F9", zeroline=True, zerolinecolor="#CBD5E1"),
            yaxis=dict(title="价格 (USDT)", showgrid=True, gridcolor="#F1F5F9",
                       tickformat=".0f", tickfont=dict(family="JetBrains Mono", size=10)),
            legend=dict(orientation="h", y=1.05),
            margin=dict(l=0, r=0, t=50, b=0),
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        col1, col2, col3, col4 = st.columns(4, gap="small")
        with col1: card(metric_mini("多单最大爆仓区", f"${price_levels[max_long_idx]:,.0f}", "向上磁吸区域", "#10B981"))
        with col2: card(metric_mini("空单最大爆仓区", f"${price_levels[max_short_idx]:,.0f}", "向下磁吸区域", "#EF4444"))
        with col3: card(metric_mini("多空爆仓比", f"{long_liq.sum()/max(short_liq.sum(),1):.2f}", "多头占优>1.2", "#3B82F6"))
        with col4: card(metric_mini("24H总清算规模", f"${(long_liq.sum()+short_liq.sum())/10:.0f}万U", "模拟聚合数据", "#8B5CF6"))
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 链上巨鲸
# ══════════════════════════════════════════════════════════════════════════════

def render_onchain():
    st.markdown('<div style="font-size:24px;font-weight:800;color:#0F172A;margin-bottom:1.2rem">🌊 链上巨鲸 · 数据监控</div>', unsafe_allow_html=True)

    # Whale alert simulation
    np.random.seed(int(time.time() / 60))
    wallets = ["0x3a8d...f9e1", "bc1q4...7k2p", "0x7c1f...a3d9", "bc1p9...m5x1", "0xd4e2...b8f3"]
    exchanges = ["Binance", "OKX", "Coinbase", "Unknown Wallet", "Kraken", "Cold Wallet"]
    coins = ["BTC", "ETH", "BTC", "ETH", "BTC"]
    directions = ["转入交易所 ⚠️", "转出交易所 🟢", "钱包间转移", "转入交易所 ⚠️", "转出交易所 🟢"]
    sentiment = ["利空", "利好", "中性", "利空", "利好"]
    s_colors = ["#EF4444", "#10B981", "#F59E0B", "#EF4444", "#10B981"]

    amounts = np.random.uniform(500, 8000, 5)
    times_ago = np.random.randint(1, 60, 5)
    values_usd = amounts * np.where(np.array(coins) == "BTC", 104800, 3950)

    rows_html = ""
    for i in range(5):
        rows_html += f"""
<tr style="border-bottom:1px solid #F1F5F9">
<td style="padding:10px 8px;font-size:12px;color:#94A3B8;font-family:JetBrains Mono,monospace">{times_ago[i]}分钟前</td>
<td style="padding:10px 8px"><span style="background:#{'DBEAFE' if coins[i]=='BTC' else 'EDE9FE'};color:#{'1D4ED8' if coins[i]=='BTC' else '6D28D9'};padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">{coins[i]}</span></td>
<td style="padding:10px 8px;font-size:14px;font-weight:700;color:#0F172A;font-family:JetBrains Mono,monospace">{amounts[i]:,.0f} {coins[i]}</td>
<td style="padding:10px 8px;font-size:12px;color:#475569">${values_usd[i]/1e6:.1f}M</td>
<td style="padding:10px 8px;font-size:12px;color:#64748B">{wallets[i]} → {random.choice(exchanges)}</td>
<td style="padding:10px 8px;font-size:12px;color:#64748B">{directions[i]}</td>
<td style="padding:10px 8px"><span style="background:{s_colors[i]}22;color:{s_colors[i]};padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700">{sentiment[i]}</span></td>
</tr>"""

    st.markdown(f"""
<div style="background:#fff;border-radius:16px;padding:1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.05);border:1px solid #F1F5F9;margin-bottom:1.2rem;overflow-x:auto">
<p style="margin:0 0 1rem;font-size:11px;font-weight:700;color:#94A3B8;letter-spacing:.8px">🐳 大额链上转账异动 · 实时播报</p>
<table style="width:100%;border-collapse:collapse">
<thead><tr style="border-bottom:2px solid #F1F5F9">
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">时间</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">币种</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">数量</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">价值</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">地址流向</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">类型</th>
<th style="padding:8px;font-size:10px;color:#94A3B8;text-align:left;font-weight:600">信号</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

    # Exchange net flow
    st.markdown('<p style="font-size:13px;font-weight:700;color:#64748B;margin:.5rem 0">交易所净流量 · BTC (近30日)</p>', unsafe_allow_html=True)
    dates = [(datetime.now() - timedelta(days=30-i)).strftime("%m/%d") for i in range(30)]
    flows = np.random.normal(0, 1500, 30)
    flows[5] = -4200; flows[12] = 3800; flows[20] = -3100; flows[27] = 2900
    fig = go.Figure()
    colors_flow = ["#10B981" if v < 0 else "#EF4444" for v in flows]
    fig.add_trace(go.Bar(x=dates, y=flows, marker_color=colors_flow, name="净流量"))
    fig.add_hline(y=0, line=dict(color="#CBD5E1", width=1))
    fig.update_layout(
        height=220, paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, tickfont=dict(size=9)),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=9, family="JetBrains Mono"), title="BTC"),
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter"),
        annotations=[dict(x=0.02, y=0.95, xref="paper", yref="paper", text="<b>净流出(绿)=利好 · 净流入(红)=利空</b>", showarrow=False, font=dict(size=10, color="#64748B"))]
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Whale wallet tracker
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1: card(metric_mini("活跃巨鲸钱包", "1,247", "过去24小时", "#3B82F6"))
    with col2: card(metric_mini("交易所BTC净流出", "-12,340 BTC", "近7日累计", "#10B981"))
    with col3: card(metric_mini("长期持有者占比", "73.4%", "LTH Supply %", "#8B5CF6"))
    with col4: card(metric_mini("矿工持仓变化", "+420 BTC", "近24小时", "#F59E0B"))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 消息面
# ══════════════════════════════════════════════════════════════════════════════

def render_sentiment():
    st.markdown('<div style="font-size:24px;font-weight:800;color:#0F172A;margin-bottom:1.2rem">📰 消息面 · 情绪实时分析</div>', unsafe_allow_html=True)

    # Fear & Greed Gauge
    fg_value = random.randint(48, 78)
    fg_label = "极度贪婪" if fg_value > 75 else "贪婪" if fg_value > 55 else "中性" if fg_value > 45 else "恐慌" if fg_value > 25 else "极度恐慌"
    fg_color = "#10B981" if fg_value > 55 else "#F59E0B" if fg_value > 45 else "#EF4444"

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fg_value,
        title={"text": f"恐慌贪婪指数 · {fg_label}", "font": {"size": 14, "color": "#64748B"}},
        number={"font": {"size": 40, "family": "JetBrains Mono", "color": fg_color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
            "bar": {"color": fg_color, "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25], "color": "#FEE2E2"},
                {"range": [25, 45], "color": "#FEF3C7"},
                {"range": [45, 55], "color": "#F1F5F9"},
                {"range": [55, 75], "color": "#D1FAE5"},
                {"range": [75, 100], "color": "#A7F3D0"},
            ],
            "threshold": {"line": {"color": fg_color, "width": 3}, "thickness": 0.8, "value": fg_value},
        },
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=0), paper_bgcolor="white", font=dict(family="Inter"))

    col_gauge, col_news = st.columns([1, 2], gap="medium")
    with col_gauge:
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
        card(f"""
<div style="text-align:center">
{metric_mini("当前指数", str(fg_value), fg_label, fg_color)}
{metric_mini("昨日指数", str(fg_value - random.randint(-8,8)), "对比昨日", "#94A3B8")}
<p style="font-size:11px;color:#94A3B8;margin-top:.5rem">数据源: Alternative.me</p>
</div>
""", padding="1rem")

    with col_news:
        # News simulation
        news_items = [
            ("🟢 利好", "#10B981", "ETF 净流入再创新高", "贝莱德 Bitcoin ETF 单日净流入突破 6.2 亿美元，机构需求持续强劲。", "3分钟前", "宏观"),
            ("🔴 利空", "#EF4444", "美联储鹰派表态压制风险资产", "FOMC 委员表示暂不考虑降息，美元指数短线走强至 104.8。", "18分钟前", "宏观"),
            ("🟢 利好", "#10B981", "MicroStrategy 再次增持 BTC", "Strategy 宣布额外购入 2,138 枚比特币，总持仓超过 21.4 万枚。", "41分钟前", "机构"),
            ("⚪ 中性", "#F59E0B", "以太坊 Dencun 升级后活跃地址回升", "链上数据显示以太坊日活跃地址突破 55 万，L2 生态蓬勃发展。", "1小时前", "链上"),
            ("🔴 利空", "#EF4444", "美国 SEC 对加密平台展开新一轮调查", "监管消息面压制短期情绪，市场短线出现波动。", "2小时前", "监管"),
            ("🟢 利好", "#10B981", "萨尔瓦多比特币持仓浮盈超1亿美元", "国家级持仓者盈利持续扩大，比特币全球认可度提升。", "3小时前", "宏观"),
        ]
        news_html = ""
        for badge, bc, title, desc, t, tag in news_items:
            news_html += f"""
<div style="display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #F1F5F9;align-items:flex-start">
<span style="font-size:12px;font-weight:700;color:{bc};white-space:nowrap;margin-top:2px">{badge}</span>
<div style="flex:1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<p style="margin:0;font-size:13px;font-weight:600;color:#0F172A">{title}</p>
<span style="background:#F1F5F9;color:#64748B;padding:1px 8px;border-radius:6px;font-size:10px">{tag}</span>
</div>
<p style="margin:0;font-size:12px;color:#64748B;line-height:1.5">{desc}</p>
<p style="margin:4px 0 0;font-size:11px;color:#94A3B8">{t}</p>
</div>
</div>"""
        card(f'<p style="margin:0 0 .5rem;font-size:11px;font-weight:700;color:#94A3B8;letter-spacing:.8px">最新宏观资讯</p>{news_html}', padding="1.2rem")

    # Sentiment trend chart
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    dates7 = [(datetime.now() - timedelta(days=6-i)).strftime("%m/%d") for i in range(7)]
    fg_history = [38, 45, 52, 61, 58, 68, fg_value]
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=dates7, y=fg_history, fill="tozeroy",
        fillcolor="rgba(59,130,246,.08)", line=dict(color="#3B82F6", width=2),
        mode="lines+markers", marker=dict(size=6, color="#3B82F6"),
    ))
    fig_trend.add_hrect(y0=75, y1=100, fillcolor="rgba(16,185,129,.05)", line_width=0, annotation_text="极度贪婪", annotation_font_size=9)
    fig_trend.add_hrect(y0=0, y1=25, fillcolor="rgba(239,68,68,.05)", line_width=0, annotation_text="极度恐慌", annotation_font_size=9)
    fig_trend.update_layout(
        title=dict(text="近7日恐慌贪婪指数趋势", font=dict(size=12, color="#64748B")),
        height=180, paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=9)),
        margin=dict(l=0, r=0, t=30, b=0), font=dict(family="Inter"),
    )
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    # Macro data grid
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1: card(metric_mini("BTC 融资费率", f"+{random.uniform(0.005,0.09):.3f}%", "永续合约 · 8H", "#3B82F6"))
    with col2: card(metric_mini("ETH 融资费率", f"+{random.uniform(0.002,0.06):.3f}%", "永续合约 · 8H", "#8B5CF6"))
    with col3: card(metric_mini("全网多空比", f"{random.uniform(1.1,1.8):.2f}", "多头偏多 > 1.0", "#10B981"))
    with col4: card(metric_mini("加密市值总量", f"${random.uniform(3.1,3.5):.2f}T", "较昨日 +1.2%", "#F59E0B"))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 联系
# ══════════════════════════════════════════════════════════════════════════════

def render_contact():
    st.markdown('<div style="font-size:24px;font-weight:800;color:#0F172A;margin-bottom:1.5rem">📞 联系专属主理人</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="max-width:600px;margin:0 auto">
<div style="background:#fff;border-radius:24px;padding:2.5rem;box-shadow:0 4px 24px rgba(0,0,0,.07);text-align:center;border:1px solid #F1F5F9">
<div style="width:80px;height:80px;background:linear-gradient(135deg,#3B82F6,#8B5CF6);border-radius:24px;display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 1.5rem">⬡</div>
<h2 style="margin:0 0 .5rem;font-size:22px;font-weight:800;color:#0F172A">AEGIS QUANT 主理人</h2>
<p style="margin:0 0 2rem;color:#64748B;font-size:14px">专业量化策略 · 一对一服务 · 机构级风控指导</p>
<div style="background:#F0F9FF;border-radius:16px;padding:1.5rem;border:1px solid #BAE6FD;margin-bottom:1.5rem">
<p style="margin:0 0 .5rem;font-size:12px;font-weight:700;color:#0284C7;letter-spacing:.5px">TELEGRAM 官方联系</p>
<p style="margin:0;font-size:28px;font-weight:800;color:#0F172A;font-family:JetBrains Mono,monospace">@bocheng668</p>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;text-align:left">
<div style="background:#F8FAFC;border-radius:12px;padding:1rem">
<p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#94A3B8">服务内容</p>
<p style="margin:0;font-size:13px;color:#475569;line-height:1.6">✦ 实时策略播报<br>✦ 精准点位提示<br>✦ 风控仓位管理<br>✦ 宏观研判解读</p>
</div>
<div style="background:#F8FAFC;border-radius:12px;padding:1rem">
<p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#94A3B8">合作模式</p>
<p style="margin:0;font-size:13px;color:#475569;line-height:1.6">✦ 节点授权 (免费)<br>✦ Pro API 50U/月<br>✦ 机构定制服务<br>✦ API 接入对接</p>
</div>
</div>
<div style="margin-top:1.5rem;background:#FFFBEB;border-radius:12px;padding:1rem;border-left:3px solid #F59E0B">
<p style="margin:0;font-size:12px;color:#92400E;line-height:1.6">⚠️ 请认准唯一官方 Telegram: <b>@bocheng668</b>，谨防假冒。本平台不提供任何投资保本承诺，所有分析仅供参考。</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TOP HEADER BAR
# ══════════════════════════════════════════════════════════════════════════════

def render_topbar():
    btc_p = get_market_data("BTC", ttl=5).iloc[-1]["close"]
    eth_p = get_market_data("ETH", ttl=5).iloc[-1]["close"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"""
<div style="background:#0F172A;padding:8px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin:-1rem -1.5rem 1.2rem;border-radius:0">
<div style="display:flex;align-items:center;gap:6px">
<span style="font-size:13px;font-weight:800;color:#F8FAFC;letter-spacing:-0.5px">⬡ AEGIS QUANT</span>
<span style="background:#10B981;color:#ECFDF5;padding:1px 8px;border-radius:4px;font-size:10px;font-weight:700">LIVE</span>
</div>
<div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap">
<span style="font-size:12px;color:#94A3B8">₿ BTC <span style="color:#F8FAFC;font-weight:700;font-family:JetBrains Mono,monospace">${btc_p:,.0f}</span></span>
<span style="font-size:12px;color:#94A3B8">Ξ ETH <span style="color:#F8FAFC;font-weight:700;font-family:JetBrains Mono,monospace">${eth_p:,.2f}</span></span>
<span style="font-size:11px;color:#475569">{now}</span>
</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.authenticated:
        render_gate()
        return

    render_sidebar()
    render_topbar()

    page = st.session_state.page
    if "核心策略" in page:
        render_strategy()
    elif "清算" in page:
        render_liquidation()
    elif "链上" in page or "巨鲸" in page:
        render_onchain()
    elif "消息" in page or "情绪" in page:
        render_sentiment()
    elif "联系" in page:
        render_contact()

    # Auto refresh every 5s
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
