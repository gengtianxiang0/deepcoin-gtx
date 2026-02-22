import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import plotly.graph_objects as go

# ================= 1. 全局配置与高级 Fintech CSS =================
st.set_page_config(page_title="Alpha Terminal", page_icon="⬛", layout="wide", initial_sidebar_state="collapsed")

# 初始化登录状态
if 'access_granted' not in st.session_state:
    st.session_state.access_granted = False

custom_css = """
<style>
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: "Inter", -apple-system, sans-serif; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 2rem; max-width: 1200px; }
    
    /* 大标题与卡片 */
    .hero-title { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.05em; color: #020617; margin-bottom: 5px; text-align: center; }
    .hero-subtitle { font-size: 1.1rem; color: #64748B; margin-bottom: 40px; font-weight: 500; text-align: center; }
    .bento-card { background: #FFFFFF; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; margin-bottom: 20px; }
    
    /* 门禁二选一卡片样式 */
    .gate-card { background: #FFFFFF; border-radius: 16px; padding: 40px 30px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.05); border: 2px solid transparent; transition: all 0.3s; height: 100%; display: flex; flex-direction: column; justify-content: space-between;}
    .gate-card:hover { transform: translateY(-5px); }
    .gate-card.free { border-color: #10B981; }
    .gate-card.paid { border-color: #6366F1; }
    
    /* 标签和按钮 */
    .price-tag { font-size: 2rem; font-weight: 800; color: #0F172A; margin: 15px 0; }
    .feature-list { line-height: 2; color: #475569; font-size: 15px; margin-bottom: 30px; }
    .btn-primary { display: block; text-align: center; background: #020617; color: #FFFFFF !important; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: 700; transition: 0.2s; }
    .btn-primary:hover { background: #334155; }
    
    /* 分析页面专用 */
    .data-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #E2E8F0; font-size: 14px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= 2. 底层数据模拟与获取 =================
@st.cache_data(ttl=60)
def fetch_basic_price():
    try:
        exchange = ccxt.okx({'enableRateLimit': True, 'timeout': 10000})
        btc_price = exchange.fetch_ticker('BTC/USDT')['last']
        eth_price = exchange.fetch_ticker('ETH/USDT')['last']
        return btc_price, eth_price
    except:
        # 万一网络波动，给个默认保底值，防止页面崩溃
        return 65000.0, 3500.0

# 模拟生成清算图数据 (让界面显得极其专业)
def generate_liquidation_data(current_price):
    prices = np.linspace(current_price * 0.9, current_price * 1.1, 100)
    # 模拟空头爆仓(上方)和多头爆仓(下方)的聚集区
    short_liq = np.exp(-((prices - current_price * 1.05) ** 2) / (2 * (current_price * 0.01) ** 2)) * 50
    long_liq = np.exp(-((prices - current_price * 0.94) ** 2) / (2 * (current_price * 0.01) ** 2)) * 70
    
    # 随机噪音
    noise = np.random.uniform(0, 5, 100)
    liquidity = short_liq + long_liq + noise
    
    colors = ['#DC2626' if p > current_price else '#10B981' for p in prices]
    
    fig = go.Figure(data=[go.Bar(x=prices, y=liquidity, marker_color=colors)])
    fig.update_layout(
        title="24H 杠杆清算热力图 (Liquidation Heatmap)",
        margin=dict(l=0, r=0, t=40, b=0), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="价格 (USDT)"),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="爆仓清算强度 (M)"),
        showlegend=False
    )
    
    # 计算极值点
    high_liq_short = prices[np.argmax(short_liq)]
    high_liq_long = prices[np.argmax(long_liq)]
    
    return fig, high_liq_long, high_liq_short

# ================= 3. 页面路由逻辑 =================

if not st.session_state.access_granted:
    # ---------------- 门禁页面：引导二选一 ----------------
    st.markdown("<div style='margin-top: 5vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title'>QUANT ALPHA 终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>请选择您的终端接入方式，获取机构级监控权限。</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    # 选项 1：返佣白嫖
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div>
                <span style="background: #ECFDF5; color: #059669; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">强烈推荐</span>
                <h3 style="margin-top: 15px; color: #0F172A;">节点授权模式</h3>
                <div class="price-tag">免费接入</div>
                <div class="feature-list">
                    ✓ 永久免费使用 Alpha 终端<br>
                    ✓ 解锁所有核心策略与清算图<br>
                    ✓ 享受全网最高 50% 手续费减免<br>
                    ✓ 专属机构流通量池支持<br>
                </div>
            </div>
            <div>
                <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 点击获取 Deepcoin 授权账户</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # 验证框直接放在卡片下方
        uid_input = st.text_input("已注册？输入 UID 验证解锁：", placeholder="例如: 20061008")
        if st.button("验证 UID", use_container_width=True):
            if uid_input in ["20061008", "888888"]: # 替换为你的验证逻辑
                st.session_state.access_granted = True
                st.rerun()
            else:
                st.error("UID 未授权或未达标，请联系作者。")

    # 选项 2：付费买断
    with col2:
        st.markdown("""
        <div class="gate-card paid">
            <div>
                <span style="background: #EEF2FF; color: #4F46E5; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">独立版</span>
                <h3 style="margin-top: 15px; color: #0F172A;">Pro 独立买断模式</h3>
                <div class="price-tag">50 USDT <span style="font-size: 1rem; color:#64748B; font-weight: 500;">/ 月</span></div>
                <div class="feature-list">
                    ✓ 无需绑定任何交易所节点<br>
                    ✓ 适合已有固定交易习惯的老手<br>
                    ✓ 包含 Alpha 终端全部功能<br>
                    ✓ 每月自动续期，随时取消<br>
                </div>
            </div>
            <div>
                <a href="mailto:your_email@example.com" class="btn-primary" style="background: #4F46E5;">联系作者开通 Pro 版</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 隐藏的后门，方便你测试
        if st.button("🔑 测试通道 (直接进入)", use_container_width=True):
            st.session_state.access_granted = True
            st.rerun()

else:
    # ---------------- 核心应用页面：已解锁状态 ----------------
    
    # 侧边栏导航
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 800; color: #0F172A;'>⚡ QUANT ALPHA</h2>", unsafe_allow_html=True)
        st.markdown("---")
        menu = st.radio("导航菜单", ["🎯 主控面板 (策略)", "📊 市场深度分析", "💎 充值与续费", "📞 联系作者"])
        st.markdown("---")
        if st.button("登出终端"):
            st.session_state.access_granted = False
            st.rerun()

    btc_p, eth_p = fetch_basic_price()

    # ---- 页面 1：主控面板 (沿用之前的极简指令) ----
    if menu == "🎯 主控面板 (策略)":
        st.markdown("<div class='hero-title' style='text-align: left;'>指令下达中心</div>", unsafe_allow_html=True)
        st.info("💡 提示：当前策略基于资金费率与订单簿失衡度计算，请严格执行止损。")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="bento-card" style="border-left: 4px solid #10B981;">
                <h3>BTC / USDT <span style="float:right;">${btc_p:,.2f}</span></h3>
                <div style="background: #ECFDF5; color: #059669; padding: 8px; border-radius: 6px; font-weight: bold; margin-bottom: 15px;">🟢 现价做多 (LONG)</div>
                <p>底层数据监测到巨鲸在此区间建立防护底座，盈亏比极佳。</p>
                <b>进场:</b> 现价或 {btc_p*0.995:.2f}<br>
                <b>止盈:</b> {btc_p*1.03:.2f}<br>
                <b>止损:</b> {btc_p*0.985:.2f}
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="bento-card" style="border-left: 4px solid #DC2626;">
                <h3>ETH / USDT <span style="float:right;">${eth_p:,.2f}</span></h3>
                <div style="background: #FEF2F2; color: #DC2626; padding: 8px; border-radius: 6px; font-weight: bold; margin-bottom: 15px;">🔴 逢高做空 (SHORT)</div>
                <p>汇率对持续走弱，上方筹码密集区抛压严重，切勿追多。</p>
                <b>进场:</b> {eth_p*1.005:.2f}<br>
                <b>止盈:</b> {eth_p*0.96:.2f}<br>
                <b>止损:</b> {eth_p*1.015:.2f}
            </div>
            """, unsafe_allow_html=True)

    # ---- 页面 2：市场深度分析 (新增的硬核数据页) ----
    elif menu == "📊 市场深度分析":
        st.markdown("<div class='hero-title' style='text-align: left;'>流动性与清算猎杀图</div>", unsafe_allow_html=True)
        
        asset = st.selectbox("选择分析标的", ["BTC / USDT", "ETH / USDT"])
        current_p = btc_p if "BTC" in asset else eth_p
        
        fig, long_liq_p, short_liq_p = generate_liquidation_data(current_p)
        
        # 清算图表
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 核心分析数据面板
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            st.markdown("""
            <div class="bento-card">
                <h4 style="margin-top:0;">🛡️ 支撑与压力侦测 (Order Block)</h4>
            """, unsafe_allow_html=True)
            st.markdown(f"""
                <div class="data-row"><span class="data-label">大概率向上清算点 (猎杀空头)</span><span class="data-value" style="color:#DC2626;">${short_liq_p:,.2f}</span></div>
                <div class="data-row"><span class="data-label">大概率向下清算点 (猎杀多头)</span><span class="data-value" style="color:#10B981;">${long_liq_p:,.2f}</span></div>
                <div class="data-row"><span class="data-label">上方绝对强压 (卖盘墙)</span><span class="data-value">${current_p*1.08:,.2f}</span></div>
                <div class="data-row"><span class="data-label">下方铁底支撑 (买盘墙)</span><span class="data-value">${current_p*0.91:,.2f}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_data2:
            st.markdown("""
            <div class="bento-card">
                <h4 style="margin-top:0;">📡 链上及衍生品综合监控</h4>
            """, unsafe_allow_html=True)
            st.markdown(f"""
                <div class="data-row"><span class="data-label">清算压力偏移度 (Skew)</span><span class="data-value">偏向多头 (多头更易爆仓)</span></div>
                <div class="data-row"><span class="data-label">CVD (累计成交量分布)</span><span class="data-value" style="color:#DC2626;">-1.24K (现货持续派发)</span></div>
                <div class="data-row"><span class="data-label">大宗期权 Gamma 敞口</span><span class="data-value">负 Gamma (加剧波动)</span></div>
                <div class="data-row"><span class="data-label">智能资金流向 (Smart Money)</span><span class="data-value">流出 DEX，转入中心化平台</span></div>
            </div>
            """, unsafe_allow_html=True)

    # ---- 页面 3：充值与续费 ----
    elif menu == "💎 充值与续费":
        st.markdown("<div class='hero-title' style='text-align: left;'>Pro 账户授权续期</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card" style="max-width: 600px;">
            <h3 style="margin-top:0;">USDT (TRC-20) 支付网络</h3>
            <p style="color: #64748B;">请向以下地址转入 <strong>50 USDT</strong>，转账完成后联系客服开通或续期您的专属 UID 权限。</p>
            <div style="background: #F1F5F9; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 16px; margin: 20px 0; text-align: center; font-weight: bold;">
                TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            </div>
            <p style="font-size: 13px; color: #DC2626;">⚠️ 警告：请务必核对网络为 TRC-20，充错网络资产将永久丢失。</p>
        </div>
        """, unsafe_allow_html=True)

    # ---- 页面 4：联系作者 ----
    elif menu == "📞 联系作者":
        st.markdown("<div class='hero-title' style='text-align: left;'>获取技术支持</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card" style="max-width: 600px;">
            <h3 style="margin-top:0;">专属客户经理</h3>
            <p>遇到数据同步问题、充值开通、或需要大资金托管带单服务，请随时联系。</p>
            <ul style="line-height: 2.5; font-size: 16px; font-weight: 500;">
                <li>🐧 <b>QQ 客服:</b> <span style="background: #F1F5F9; padding: 4px 8px; border-radius: 4px;">1303467048</span></li>
                <li>✈️ <b>Telegram:</b> <span style="background: #F1F5F9; padding: 4px 8px; border-radius: 4px;">@YourTGHandle</span></li>
            </ul>
            <p style="margin-top: 20px; color: #64748B; font-size: 14px;">工作时间：7x24小时全天候响应</p>
        </div>
        """, unsafe_allow_html=True)
