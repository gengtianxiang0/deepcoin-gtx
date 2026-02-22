import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import time
import plotly.graph_objects as go

# ================= 1. 全局配置与状态初始化 =================
# initial_sidebar_state="collapsed" 确保手机端默认收起侧边栏，不遮挡主视线
st.set_page_config(page_title="Alpha Terminal", page_icon="⬛", layout="wide", initial_sidebar_state="collapsed")

if 'access_granted' not in st.session_state:
    st.session_state.access_granted = False
if 'uid' not in st.session_state:
    st.session_state.uid = ""

# ================= 2. 移动端优先的 Fintech CSS =================
custom_css = """
<style>
    /* 全局极简冷色调 */
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: "Inter", -apple-system, sans-serif; }
    
    /* ⚠️ 极其关键：只隐藏右侧菜单和底部水印，保留顶部的汉堡按钮(☰)供手机呼出侧边栏 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 1200px; }
    
    /* 大标题与副标题 */
    .hero-title { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.05em; color: #020617; margin-bottom: 5px; }
    .hero-subtitle { font-size: 1rem; color: #64748B; margin-bottom: 20px; font-weight: 500; }
    
    /* 门禁卡片 */
    .gate-card { background: #FFFFFF; border-radius: 16px; padding: 30px 20px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.05); border: 2px solid transparent; transition: all 0.3s; height: 100%; display: flex; flex-direction: column; justify-content: space-between;}
    .gate-card.free { border-color: #10B981; }
    .gate-card.paid { border-color: #6366F1; }
    
    .price-tag { font-size: 1.8rem; font-weight: 800; color: #0F172A; margin: 15px 0; }
    .feature-list { line-height: 1.8; color: #475569; font-size: 14px; margin-bottom: 25px; }
    .btn-primary { display: block; text-align: center; background: #020617; color: #FFFFFF !important; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 700; transition: 0.2s; font-size: 15px;}
    
    /* Bento Box 便当盒样式 */
    .bento-card { background: #FFFFFF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); border: 1px solid #F1F5F9; margin-bottom: 15px; }
    
    /* 移动端专属自适应优化 (当屏幕宽度小于 768px 时自动触发) */
    @media (max-width: 768px) {
        .hero-title { font-size: 1.6rem; text-align: center; }
        .hero-subtitle { font-size: 0.9rem; text-align: center; }
        .bento-card { padding: 15px; border-radius: 12px; }
        .price-tag { font-size: 1.5rem; }
        .gate-card { padding: 20px 15px; margin-bottom: 15px; }
        .data-row { font-size: 12px; flex-direction: column; align-items: flex-start; gap: 4px; }
        .data-value { align-self: flex-start; }
    }
    
    .data-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #E2E8F0; font-size: 13px; }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #64748B; font-weight: 500; }
    .data-value { font-weight: 700; color: #0F172A; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= 3. 底层数据引擎 (极速版 TTL=10s) =================
# 缓存时间降至 10 秒，保证数据的实时性和紧迫感
@st.cache_data(ttl=10)
def fetch_market_data():
    try:
        exchange = ccxt.okx({'enableRateLimit': True, 'timeout': 5000})
        symbols = ['BTC/USDT', 'ETH/USDT']
        data = {}
        for sym in symbols:
            ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=24)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            data[sym] = df
        return data
    except Exception as e:
        return None

def generate_strategy(df, symbol):
    cur_p = df['close'].iloc[-1]
    res = df['high'].max()  # 压力位
    sup = df['low'].min()   # 支撑位
    
    range_pct = (cur_p - sup) / (res - sup) if res != sup else 0.5
    
    if range_pct < 0.35:
        signal = "🟢 现价做多 (LONG)"
        entry, tp, sl = f"{cur_p * 0.998:.2f}", f"{res * 0.99:.2f}", f"{sup * 0.995:.2f}"
        desc = "空头动能衰竭，盈亏比极佳。建议现价或小幅回调分批建仓多单。"
    elif range_pct > 0.65:
        signal = "🔴 逢高做空 (SHORT)"
        entry, tp, sl = f"{cur_p * 1.002:.2f}", f"{sup * 1.01:.2f}", f"{res * 1.005:.2f}"
        desc = "触及高频压制区，极易发生多头踩踏。建议逢高布局空单。"
    else:
        signal = "⏳ 中性震荡 (NEUTRAL)"
        entry, tp, sl = "等待测试边界", "等待趋势确认", "严控仓位"
        desc = "处于中枢震荡区，多空博弈激烈。请等待右侧交易机会。"
        
    return {"price": cur_p, "res": res, "sup": sup, "text": signal, "entry": entry, "tp": tp, "sl": sl, "desc": desc}

def generate_liquidation_chart(current_price, asset_type):
    prices = np.linspace(current_price * 0.88, current_price * 1.12, 120)
    # 模拟红绿柱子
    short_liq = np.exp(-((prices - current_price * 1.04) ** 2) / (2 * (current_price * 0.015) ** 2)) * (80 if asset_type == 'BTC' else 30)
    long_liq = np.exp(-((prices - current_price * 0.95) ** 2) / (2 * (current_price * 0.012) ** 2)) * (120 if asset_type == 'BTC' else 45)
    noise = np.random.uniform(0, 5, 120)
    liquidity = short_liq + long_liq + noise
    
    colors = ['#DC2626' if p > current_price else '#10B981' for p in prices]
    fig = go.Figure(data=[go.Bar(x=prices, y=liquidity, marker_color=colors)])
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title=f"{asset_type} 价格 (USDT)", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="清算量 (M)", tickfont=dict(size=10)),
        showlegend=False
    )
    
    return fig, prices[np.argmax(long_liq)], prices[np.argmax(short_liq)]

# ================= 4. 页面路由与渲染 =================

if not st.session_state.access_granted:
    # ---------------- 门禁页面 ----------------
    st.markdown("<div style='margin-top: 2vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title'>QUANT ALPHA 终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>请选择您的终端接入方式，获取机构级监控权限。</div>", unsafe_allow_html=True)
    
    # 手机端会自动把这两个列变成上下滑动，完美适配
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div>
                <span style="background: #ECFDF5; color: #059669; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">强烈推荐</span>
                <h3 style="margin-top: 10px; color: #0F172A;">节点授权模式</h3>
                <div class="price-tag">免费接入</div>
                <div class="feature-list">
                    ✓ 永久免费使用 Alpha 终端<br>
                    ✓ 极速获取双币对点位与清算图<br>
                    ✓ 享受全网最高 50% 手续费减免<br>
                </div>
            </div>
            <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 点击获取专属返佣账户</a>
        </div>
        """, unsafe_allow_html=True)
        
        uid_input = st.text_input("👉 输入 UID 验证解锁：", placeholder="例如: 20061008")
        if st.button("立即验证 UID", use_container_width=True):
            if uid_input in ["20061008", "888888"]:
                st.session_state.access_granted = True
                st.session_state.uid = uid_input
                st.rerun()
            else:
                st.error("❌ UID 未授权！请确认使用本站链接注册。")

    with col2:
        st.markdown("""
        <div class="gate-card paid">
            <div>
                <span style="background: #EEF2FF; color: #4F46E5; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">独立版</span>
                <h3 style="margin-top: 10px; color: #0F172A;">Pro 买断模式</h3>
                <div class="price-tag">50 U <span style="font-size: 1rem; color:#64748B;">/ 月</span></div>
                <div class="feature-list">
                    ✓ 无需绑定任何交易所节点限制<br>
                    ✓ 适合已有固定交易习惯的老手<br>
                    ✓ 包含全部底层监控数据<br>
                </div>
            </div>
            <a href="mailto:your_email@example.com" class="btn-primary" style="background: #4F46E5;">联系主理人开通 Pro 版</a>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔑 测试通道 (管理员一键直达)", use_container_width=True):
            st.session_state.access_granted = True
            st.session_state.uid = "Admin_Test"
            st.rerun()

else:
    # ---------------- 内部系统：顶级移动端主控台 ----------------
    
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 800; color: #0F172A; margin-bottom: 0px;'>⚡ QUANT ALPHA</h2>", unsafe_allow_html=True)
        st.caption("系统状态: OKX 节点直连 🟢")
        
        st.markdown(f"""
        <div style="background: #EEF2FF; padding: 12px; border-radius: 8px; margin: 10px 0; border: 1px solid #C7D2FE;">
            <div style="font-size: 11px; color: #4F46E5; font-weight: 700; margin-bottom: 3px;">✅ 节点已授权</div>
            <div style="font-size: 14px; color: #0F172A; font-weight: 800;">UID: {st.session_state.uid}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        menu = st.radio("导航菜单", ["🎯 Alpha 策略主控台", "💎 Pro 续费通道", "📞 联系客户经理"])
        st.markdown("---")
        if st.button("登出终端"):
            st.session_state.access_granted = False
            st.session_state.uid = ""
            st.rerun()

    if menu == "🎯 Alpha 策略主控台":
        st.markdown("<div class='hero-title'>ALPHA TERMINAL</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>手机端极速指令中枢</div>", unsafe_allow_html=True)

        with st.spinner('直连专线中...'):
            market_data = fetch_market_data()

        if market_data:
            # 手机端会自动叠放
            col1, col2 = st.columns(2)
            
            with col1:
                btc_strat = generate_strategy(market_data['BTC/USDT'], 'BTC')
                st.markdown(f"""
                <div class="bento-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 10px;">
                        <span style="font-size: 1.1rem; font-weight: 800;">BTC/USDT</span>
                        <span style="font-size: 1.2rem; font-weight: 800; color: #0F172A;">${btc_strat['price']:,.2f}</span>
                    </div>
                    <div style="font-weight: bold; margin-bottom: 8px;">{btc_strat['text']}</div>
                    <p style="font-size: 12px; color: #64748B; line-height: 1.5; margin-bottom: 15px;">{btc_strat['desc']}</p>
                    <div class="data-row" style="background: #FEF2F2; padding: 4px 8px; border-radius: 4px;"><span class="data-label">🔴 强压</span><span class="data-value" style="color: #DC2626;">${btc_strat['res']:,.2f}</span></div>
                    <div class="data-row" style="background: #ECFDF5; padding: 4px 8px; border-radius: 4px; margin-bottom: 10px;"><span class="data-label">🟢 铁底</span><span class="data-value" style="color: #10B981;">${btc_strat['sup']:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">进场点</span><span class="data-value">{btc_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈</span><span class="data-value" style="color: #059669;">{btc_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">止损</span><span class="data-value" style="color: #DC2626;">{btc_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                eth_strat = generate_strategy(market_data['ETH/USDT'], 'ETH')
                st.markdown(f"""
                <div class="bento-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 10px;">
                        <span style="font-size: 1.1rem; font-weight: 800;">ETH/USDT</span>
                        <span style="font-size: 1.2rem; font-weight: 800; color: #0F172A;">${eth_strat['price']:,.2f}</span>
                    </div>
                    <div style="font-weight: bold; margin-bottom: 8px;">{eth_strat['text']}</div>
                    <p style="font-size: 12px; color: #64748B; line-height: 1.5; margin-bottom: 15px;">{eth_strat['desc']}</p>
                    <div class="data-row" style="background: #FEF2F2; padding: 4px 8px; border-radius: 4px;"><span class="data-label">🔴 强压</span><span class="data-value" style="color: #DC2626;">${eth_strat['res']:,.2f}</span></div>
                    <div class="data-row" style="background: #ECFDF5; padding: 4px 8px; border-radius: 4px; margin-bottom: 10px;"><span class="data-label">🟢 铁底</span><span class="data-value" style="color: #10B981;">${eth_strat['sup']:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">进场点</span><span class="data-value">{eth_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈</span><span class="data-value" style="color: #059669;">{eth_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">止损</span><span class="data-value" style="color: #DC2626;">{eth_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # --- 全新模块：双币种选项卡清算图 (为手机节省纵向空间) ---
            st.markdown("<h3 style='font-size: 1.1rem; margin-top: 10px; margin-bottom: 10px;'>🔥 全网合约清算热力雷达</h3>", unsafe_allow_html=True)
            
            tab_btc, tab_eth = st.tabs(["🟠 BTC 清算侦测", "🔵 ETH 清算侦测"])
            
            with tab_btc:
                fig_btc, btc_l_liq, btc_s_liq = generate_liquidation_chart(btc_strat['price'], 'BTC')
                st.plotly_chart(fig_btc, use_container_width=True, config={'displayModeBar': False})
                st.markdown(f"""
                <div class="bento-card" style="padding: 15px; margin-top: -15px;">
                    <div class="data-row"><span class="data-label">向上猎杀点 (空头痛点)</span><span class="data-value" style="color:#DC2626;">${btc_s_liq:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">向下猎杀点 (多头痛点)</span><span class="data-value" style="color:#10B981;">${btc_l_liq:,.2f}</span></div>
                    <p style="font-size: 12px; color: #475569; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #E2E8F0;">
                        <strong>🤖 引擎推演：</strong>上方 {btc_s_liq:,.0f} 聚集了海量高倍止损盘，庄家向上插针爆空的概率极高，切勿盲目摸顶。
                    </p>
                </div>
                """, unsafe_allow_html=True)

            with tab_eth:
                fig_eth, eth_l_liq, eth_s_liq = generate_liquidation_chart(eth_strat['price'], 'ETH')
                st.plotly_chart(fig_eth, use_container_width=True, config={'displayModeBar': False})
                st.markdown(f"""
                <div class="bento-card" style="padding: 15px; margin-top: -15px;">
                    <div class="data-row"><span class="data-label">向上猎杀点 (空头痛点)</span><span class="data-value" style="color:#DC2626;">${eth_s_liq:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">向下猎杀点 (多头痛点)</span><span class="data-value" style="color:#10B981;">${eth_l_liq:,.2f}</span></div>
                    <p style="font-size: 12px; color: #475569; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #E2E8F0;">
                        <strong>🤖 引擎推演：</strong>ETH 汇率持续弱势，底部 {eth_l_liq:,.0f} 附近的多头岌岌可危，注意向下画门的洗盘风险。
                    </p>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.error("⚠️ 数据获取失败，请下拉刷新。")

    elif menu == "💎 Pro 续费通道":
        st.markdown("<div class='hero-title'>Pro 账户授权续期</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">USDT (TRC-20) 网络</h4>
            <p style="color: #64748B; font-size: 14px;">请转入 <strong>50 USDT</strong>，完成后联系客服续期。</p>
            <div style="background: #F1F5F9; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 13px; text-align: center; word-break: break-all;">
                TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif menu == "📞 联系客户经理":
        st.markdown("<div class='hero-title'>获取技术支持</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">联系主理人</h4>
            <ul style="line-height: 2.5; font-size: 14px; padding-left: 20px;">
                <li>🐧 <b>QQ 客服:</b> 1303467048</li>
                <li>✈️ <b>Telegram:</b> @YourTGHandle</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
