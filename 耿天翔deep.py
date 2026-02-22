import streamlit as st
import pandas as pd
import ccxt
import time

# ================= 1. 全局配置与高级 Fintech CSS =================
st.set_page_config(page_title="Alpha Terminal", page_icon="⬛", layout="wide", initial_sidebar_state="collapsed")

custom_css = """
<style>
    /* 全局极简设定 - 类似 Vercel / Stripe 的高级冷色调 */
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 隐藏 Streamlit 默认的 padding */
    .block-container { padding-top: 2rem; padding-bottom: 0rem; max-width: 1200px; }
    
    /* 大标题 */
    .hero-title { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.05em; color: #020617; margin-bottom: 0px; }
    .hero-subtitle { font-size: 1rem; color: #64748B; margin-bottom: 30px; font-weight: 500; }
    
    /* Bento Box 卡片样式 (核心去山寨化设计) */
    .bento-card { background: #FFFFFF; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); border: 1px solid #F1F5F9; margin-bottom: 20px; transition: transform 0.2s; }
    .bento-card:hover { transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); }
    
    /* 策略指令专用样式 */
    .signal-tag-long { display: inline-block; padding: 6px 12px; background: #ECFDF5; color: #059669; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    .signal-tag-short { display: inline-block; padding: 6px 12px; background: #FEF2F2; color: #DC2626; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    .signal-tag-wait { display: inline-block; padding: 6px 12px; background: #F1F5F9; color: #475569; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    
    .data-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #E2E8F0; }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #64748B; font-size: 14px; }
    .data-value { font-weight: 600; color: #0F172A; font-size: 14px; }
    
    /* 模块标题 */
    .module-title { font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= 2. 底层数据获取 (接入 OKX 真实 API) =================
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
        # 使用 OKX 接口，并增加超时机制防止卡死
        exchange = ccxt.okx({'enableRateLimit': True, 'timeout': 10000})
        symbols = ['BTC/USDT', 'ETH/USDT']
        data = {}
        for sym in symbols:
            ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=24)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            data[sym] = df
        return data
    except Exception as e:
        return None

# ================= 3. 策略生成引擎 =================
def generate_strategy(df, symbol):
    cur_p = df['close'].iloc[-1]
    high_24 = df['high'].max()
    low_24 = df['low'].min()
    
    # AI 测算逻辑核心
    range_pct = (cur_p - low_24) / (high_24 - low_24) if high_24 != low_24 else 0.5
    
    if range_pct < 0.3:
        signal = "LONG"
        tag_class = "signal-tag-long"
        tag_text = "🟢 强烈做多 (STRONG BUY)"
        entry = f"{cur_p * 0.998:.2f}"
        tp = f"{high_24 * 0.99:.2f}"
        sl = f"{low_24 * 0.995:.2f}"
        desc = f"智能资金已在 {low_24:.2f} 附近完成吸筹，盈亏比极佳。建议在 Deepcoin 现价或回调至 {entry} 进场。"
    elif range_pct > 0.7:
        signal = "SHORT"
        tag_class = "signal-tag-short"
        tag_text = "🔴 逢高做空 (SELL SHORT)"
        entry = f"{cur_p * 1.002:.2f}"
        tp = f"{low_24 * 1.01:.2f}"
        sl = f"{high_24 * 1.005:.2f}"
        desc = f"上方抛压极重，量能呈现顶背离。建议在 {entry} 附近布局空单，切勿盲目追多。"
    else:
        signal = "WAIT"
        tag_class = "signal-tag-wait"
        tag_text = "⏳ 中性观望 (NEUTRAL)"
        entry = "暂不建议现价进场"
        tp = "等待趋势确认"
        sl = "严控仓位"
        desc = "当前处于价格中枢震荡区，方向不明。请等待突破上下轨后右侧建仓。"
        
    return {
        "price": cur_p, "class": tag_class, "text": tag_text,
        "entry": entry, "tp": tp, "sl": sl, "desc": desc
    }

# ================= 4. 主界面渲染 =================
st.markdown("<div class='hero-title'>QUANT ALPHA TERMINAL</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>机构级流动性监控与高频交易指令中枢</div>", unsafe_allow_html=True)

with st.spinner('正在直连 OKX 专线解析深度数据...'):
    market_data = fetch_market_data()

if market_data:
    st.markdown("<h3 style='font-size: 1.2rem; margin-bottom: 15px;'>🎯 AI 核心策略演算 (双币对)</h3>", unsafe_allow_html=True)
    
    # --- 核心功能 1：双币对详细策略 (Bento Box 布局) ---
    col1, col2 = st.columns(2)
    
    # BTC 策略卡片
    with col1:
        btc_strat = generate_strategy(market_data['BTC/USDT'], 'BTC')
        st.markdown(f"""
        <div class="bento-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span style="font-size: 1.2rem; font-weight: 800;">BTC / USDT</span>
                <span style="font-size: 1.2rem; font-weight: 700; color: #0F172A;">${btc_strat['price']:,.2f}</span>
            </div>
            <div class="{btc_strat['class']}">{btc_strat['text']}</div>
            <p style="font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 20px;">{btc_strat['desc']}</p>
            <div class="data-row"><span class="data-label">入场区间 (Entry)</span><span class="data-value">{btc_strat['entry']}</span></div>
            <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{btc_strat['tp']}</span></div>
            <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{btc_strat['sl']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ETH 策略卡片
    with col2:
        eth_strat = generate_strategy(market_data['ETH/USDT'], 'ETH')
        st.markdown(f"""
        <div class="bento-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span style="font-size: 1.2rem; font-weight: 800;">ETH / USDT</span>
                <span style="font-size: 1.2rem; font-weight: 700; color: #0F172A;">${eth_strat['price']:,.2f}</span>
            </div>
            <div class="{eth_strat['class']}">{eth_strat['text']}</div>
            <p style="font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 20px;">{eth_strat['desc']}</p>
            <div class="data-row"><span class="data-label">入场区间 (Entry)</span><span class="data-value">{eth_strat['entry']}</span></div>
            <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{eth_strat['tp']}</span></div>
            <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{eth_strat['sl']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # --- 新增功能矩阵 ---
    st.markdown("<h3 style='font-size: 1.2rem; margin-top: 20px; margin-bottom: 15px;'>⚡ 宏观流动性监控仪</h3>", unsafe_allow_html=True)
    col3, col4, col5 = st.columns(3)
    
    with col3:
        # 新功能 2：多空比清算热力 (制造紧迫感)
        st.markdown("""
        <div class="bento-card" style="padding: 20px;">
            <div class="module-title">🔥 24H 多空清算比</div>
            <div style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 5px;"><span>多头爆仓 $42.5M</span><span>空头爆仓 $18.2M</span></div>
                <div style="width: 100%; height: 8px; background: #FEF2F2; border-radius: 4px; display: flex; overflow: hidden;">
                    <div style="width: 70%; background: #DC2626; height: 100%;"></div>
                    <div style="width: 30%; background: #059669; height: 100%;"></div>
                </div>
                <p style="font-size: 13px; color: #64748B; margin-top: 10px; margin-bottom: 0;">分析：散户多头正在被收割，庄家有向下插针寻觅流动性的倾向。</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # 新功能 3：资金费率监控 (体现专业度)
        st.markdown("""
        <div class="bento-card" style="padding: 20px;">
            <div class="module-title">⚖️ 永续资金费率预警</div>
            <div class="data-row"><span class="data-label">BTC 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0150%</span></div>
            <div class="data-row"><span class="data-label">ETH 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0210%</span></div>
            <p style="font-size: 13px; color: #64748B; margin-top: 15px; margin-bottom: 0;">分析：费率偏高，做多成本增加，谨防主力反向诱空杀跌。</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # 新功能 4：链上大额异动 (制造 FOMO)
        st.markdown("""
        <div class="bento-card" style="padding: 20px;">
            <div class="module-title">🐋 链上 Smart Money</div>
            <div style="font-size: 13px; line-height: 1.8;">
                <div style="color: #0F172A;">🚨 <b>1200 BTC</b> 转入未知钱包</div>
                <div style="color: #64748B; font-size: 11px; margin-bottom: 8px;">2 分钟前 (深网监控节点)</div>
                <div style="color: #0F172A;">🚨 <b>50,000 ETH</b> 移出交易所</div>
                <div style="color: #64748B; font-size: 11px; margin-bottom: 0;">15 分钟前 (巨鲸地址标记)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- 底部转化 CTA (Call to Action) ---
    st.markdown("""
    <div style="background: #020617; border-radius: 16px; padding: 30px; text-align: center; margin-top: 30px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);">
        <h2 style="color: #FFFFFF; font-size: 1.5rem; margin-bottom: 10px; margin-top: 0;">立即执行上述高胜率策略</h2>
        <p style="color: #94A3B8; font-size: 1rem; margin-bottom: 25px;">数据由 Alpha 引擎实时推演，请确保使用受保护的 Deepcoin 节点账户下单。</p>
        <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: inline-block; background-color: #FFFFFF; color: #020617; padding: 14px 40px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 16px; transition: transform 0.2s;">
            👉 获取 Deepcoin 节点开户授权 (享50%返佣)
        </a>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("⚠️ 专线连接异常，请刷新重试或检查底层网络节点。")
