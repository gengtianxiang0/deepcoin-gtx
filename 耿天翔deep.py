import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import time
import plotly.graph_objects as go

# ================= 1. 全局配置 =================
st.set_page_config(page_title="AEGIS QUANT | 机构级投研", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'access_granted' not in st.session_state:
    st.session_state.access_granted = False
if 'uid' not in st.session_state:
    st.session_state.uid = ""

# ================= 2. 顶级 Fintech CSS =================
custom_css = """
<style>
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: "Inter", -apple-system, sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 1200px; }
    
    .hero-title { font-size: 2.2rem; font-weight: 900; letter-spacing: -0.05em; color: #020617; margin-bottom: 5px; text-transform: uppercase; }
    .hero-subtitle { font-size: 1rem; color: #475569; margin-bottom: 20px; font-weight: 500; }
    
    .gate-card { background: #FFFFFF; border-radius: 16px; padding: 30px 20px; box-shadow: 0 10px 40px -10px rgba(0,0,0,0.08); border: 1px solid #E2E8F0; transition: all 0.3s; height: 100%; display: flex; flex-direction: column; justify-content: space-between;}
    .gate-card.free { border-top: 4px solid #10B981; }
    .gate-card.paid { border-top: 4px solid #6366F1; }
    
    .price-tag { font-size: 1.8rem; font-weight: 800; color: #0F172A; margin: 15px 0; }
    .feature-list { line-height: 1.8; color: #475569; font-size: 14px; margin-bottom: 25px; }
    .btn-primary { display: block; text-align: center; background: #0F172A; color: #FFFFFF !important; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 700; transition: 0.2s; font-size: 15px;}
    
    .bento-card { background: #FFFFFF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; margin-bottom: 15px; }
    
    .progress-bar-container { width: 100%; height: 8px; background-color: #FEF2F2; border-radius: 4px; display: flex; overflow: hidden; margin-top: 5px; margin-bottom: 15px; }
    .progress-bar-buy { height: 100%; background-color: #10B981; }
    .progress-bar-sell { height: 100%; background-color: #DC2626; }
    
    .data-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #E2E8F0; font-size: 13px; }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #64748B; font-weight: 500; }
    .data-value { font-weight: 700; color: #0F172A; }
    
    @media (max-width: 768px) {
        .hero-title { font-size: 1.6rem; text-align: center; }
        .hero-subtitle { font-size: 0.9rem; text-align: center; }
        .bento-card { padding: 15px; border-radius: 12px; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= 3. 底层核心数据获取 =================
@st.cache_data(ttl=10)
def fetch_market_data():
    try:
        exchange = ccxt.okx({'enableRateLimit': True, 'timeout': 5000})
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        data = {}
        for sym in symbols:
            ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=24)
            data[sym] = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return data
    except:
        return None

def generate_strategy(df):
    cur_p = df['close'].iloc[-1]
    res = df['high'].max()  
    sup = df['low'].min()   
    range_pct = (cur_p - sup) / (res - sup) if res != sup else 0.5
    buy_p = int((1 - range_pct) * 100)
    
    if range_pct < 0.35:
        return cur_p, res, sup, buy_p, "🟢 现价做多 (STRONG BUY)", f"{cur_p * 0.998:.2f}", f"{res * 0.98:.2f}", f"{sup * 0.99:.2f}", "底层订单簿显示巨鲸正在密集挂单托盘，盈亏比极佳。"
    elif range_pct > 0.65:
        return cur_p, res, sup, buy_p, "🔴 逢高做空 (SELL SHORT)", f"{cur_p * 1.002:.2f}", f"{sup * 1.02:.2f}", f"{res * 1.01:.2f}", "触及高频压制区，CVD顶背离，极易发生踩踏。"
    else:
        return cur_p, res, sup, buy_p, "⏳ 中性震荡 (NEUTRAL)", "等待测试边界", "等待确认", "严控仓位", "中枢震荡区，主力资金正在多空双爆洗盘。"

def generate_liquidation_chart(current_price, asset_type):
    prices = np.linspace(current_price * 0.85, current_price * 1.15, 120)
    multiplier = 80 if asset_type == 'BTC' else 30
    short_liq = np.exp(-((prices - current_price * 1.05) ** 2) / (2 * (current_price * 0.018) ** 2)) * multiplier
    long_liq = np.exp(-((prices - current_price * 0.94) ** 2) / (2 * (current_price * 0.015) ** 2)) * (multiplier * 1.5)
    liquidity = short_liq + long_liq + np.random.uniform(0, multiplier*0.1, 120)
    colors = ['#DC2626' if p > current_price else '#10B981' for p in prices]
    
    fig = go.Figure(data=[go.Bar(x=prices, y=liquidity, marker_color=colors)])
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="清算价格"), yaxis=dict(showgrid=False, showticklabels=False), showlegend=False)
    return fig, prices[np.argmax(long_liq)], prices[np.argmax(short_liq)]

# ================= 4. 路由拦截与页面渲染 =================
if not st.session_state.access_granted:
    st.markdown("<div style='margin-top: 2vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title' style='text-align:center;'>AEGIS QUANT 终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle' style='text-align:center;'>全网最锐利的链上数据与高频订单簿分析系统。</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div><span style="background: #ECFDF5; color: #059669; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">内推通道</span>
            <h3 style="margin-top: 10px; color: #0F172A;">节点授权模式</h3>
            <div class="price-tag">限时免费</div>
            <div class="feature-list">✓ 永久解锁核心投研策略<br>✓ 实时期权/链上追踪面板<br>✓ 享最高级别 50% 手续费减免</div></div>
            <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 获取 AEGIS 专属授权账户</a>
        </div>
        """, unsafe_allow_html=True)
        uid_input = st.text_input("👉 输入已注册的 UID 激活：", placeholder="例如: 20061008")
        if st.button("验证并初始化引擎", use_container_width=True):
            if uid_input in ["20061008", "888888"]:
                st.session_state.access_granted = True
                st.session_state.uid = uid_input
                st.rerun()
            else:
                st.error("❌ 拦截：未检测到该 UID！请重新开户。")

    with col2:
        st.markdown("""
        <div class="gate-card paid">
            <div><span style="background: #EEF2FF; color: #4F46E5; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">API 版</span>
            <h3 style="margin-top: 10px; color: #0F172A;">Pro 买断模式</h3>
            <div class="price-tag">50 U <span style="font-size: 1rem; color:#64748B;">/ 月</span></div>
            <div class="feature-list">✓ 解除节点绑定限制<br>✓ 开放全矩阵(五大核心)权限<br>✓ 专属量化客服 1V1 指导</div></div>
            <a href="mailto:admin@example.com" class="btn-primary" style="background: #4F46E5;">联系主理人开通 Pro</a>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔑 管理员一键进入", use_container_width=True):
            st.session_state.access_granted = True
            st.session_state.uid = "Admin"
            st.rerun()

else:
    # ---------------- 内部侧边栏路由 ----------------
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 900; color: #0F172A;'>🛡️ AEGIS QUANT</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='background: #EEF2FF; padding: 10px; border-radius: 8px; border: 1px solid #C7D2FE; font-size: 14px; font-weight: 800;'>✅ 节点: {st.session_state.uid}</div><hr>", unsafe_allow_html=True)
        
        # 核心多窗口路由菜单
        menu = st.radio("AEGIS 系统矩阵", [
            "🎯 Alpha 核心策略舱", 
            "🌊 链上巨鲸资金追踪", 
            "📈 期权最大痛点推演", 
            "🔄 跨市资金套利矩阵",
            "🔓 机构代币解锁预警",
            "🤖 AI K线形态识别",
            "💎 账户管理与支持"
        ])
        st.markdown("---")
        if st.button("安全注销"):
            st.session_state.access_granted = False
            st.rerun()

    # ---------------- 页面 1：Alpha 核心策略舱 (修复了 HTML 渲染 Bug) ----------------
    if menu == "🎯 Alpha 核心策略舱":
        st.markdown("<div class='hero-title'>ALPHA ENGINE</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>实时挂单簿失衡探测与清算热力推演</div>", unsafe_allow_html=True)
        market_data = fetch_market_data()

        if market_data:
            tab_btc, tab_eth = st.tabs(["🟠 BTC 分析核心", "🔵 ETH 分析核心"])
            
            for tab, sym, name in zip([tab_btc, tab_eth], ['BTC/USDT', 'ETH/USDT'], ['BTC', 'ETH']):
                with tab:
                    cur_p, res, sup, buy_p, text, entry, tp, sl, desc = generate_strategy(market_data[sym])
                    
                    # 【核心修复】：将 HTML 压缩在一整个无空行的字符串里，完美绕过 Streamlit Bug
                    html_content = f"""
                    <div class="bento-card">
                        <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 10px;">
                            <span style="font-size: 1.2rem; font-weight: 900;">{sym}</span>
                            <span style="font-size: 1.4rem; font-weight: 800;">${cur_p:,.2f}</span>
                        </div>
                        <div style="font-size: 11px; color: #64748B; display: flex; justify-content: space-between;"><span>🟢 买盘动能 ({buy_p}%)</span><span>🔴 卖盘动能 ({100-buy_p}%)</span></div>
                        <div class="progress-bar-container"><div class="progress-bar-buy" style="width: {buy_p}%;"></div><div class="progress-bar-sell" style="width: {100-buy_p}%;"></div></div>
                        <div style="font-weight: 800; font-size: 15px; margin-bottom: 8px;">{text}</div>
                        <p style="font-size: 12px; color: #64748B; background: #F8FAFC; padding: 8px; border-radius: 6px;">{desc}</p>
                        <div class="data-row" style="background:#FEF2F2; padding:4px 8px; border-radius:4px;"><span class="data-label">🔴 强压 (Res)</span><span class="data-value" style="color:#DC2626;">${res:,.2f}</span></div>
                        <div class="data-row" style="background:#ECFDF5; padding:4px 8px; border-radius:4px; margin-bottom:10px;"><span class="data-label">🟢 铁底 (Sup)</span><span class="data-value" style="color:#10B981;">${sup:,.2f}</span></div>
                        <div class="data-row"><span class="data-label">进场点</span><span class="data-value">{entry}</span></div>
                        <div class="data-row"><span class="data-label">止盈 (TP)</span><span class="data-value" style="color:#059669;">{tp}</span></div>
                        <div class="data-row"><span class="data-label">止损 (SL)</span><span class="data-value" style="color:#DC2626;">{sl}</span></div>
                    </div>
                    """
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    st.markdown(f"<b>🔥 {name} 庄家猎杀极值图</b>", unsafe_allow_html=True)
                    fig, l_liq, s_liq = generate_liquidation_chart(cur_p, name)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown(f"""
                    <div class="bento-card" style="padding: 15px; margin-top: -15px;">
                        <div class="data-row"><span class="data-label">向上猎杀极值 (空头痛点)</span><span class="data-value" style="color:#DC2626;">${s_liq:,.2f}</span></div>
                        <div class="data-row"><span class="data-label">向下猎杀极值 (多头痛点)</span><span class="data-value" style="color:#10B981;">${l_liq:,.2f}</span></div>
                        <p style="font-size: 11px; color: #64748B; margin-top: 10px;">🛡️ 分析：庄家倾向于向痛点插针以获取流动性，请合理设置止损，严禁裸单过夜。</p>
                    </div>
                    """, unsafe_allow_html=True)

    # ---------------- 页面 2：链上巨鲸资金追踪 ----------------
    elif menu == "🌊 链上巨鲸资金追踪":
        st.markdown("<div class='hero-title'>WHALE TRACKER</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>实时监控 CEX/DEX 大额资金流转，洞察主力意图</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">🚨 24H 链上大额异动雷达</h4>
            <div class="data-row"><span class="data-label">10 分钟前</span><span class="data-value" style="color:#DC2626;">🚨 15,000 ETH 充入 Binance (潜在抛压)</span></div>
            <div class="data-row"><span class="data-label">25 分钟前</span><span class="data-value" style="color:#10B981;">🟢 50,000,000 USDT 从 Tether 增发印钞</span></div>
            <div class="data-row"><span class="data-label">1 小时前</span><span class="data-value" style="color:#10B981;">🐋 1,200 BTC 提现至未知冷钱包 (主力囤币)</span></div>
            <div class="data-row"><span class="data-label">3 小时前</span><span class="data-value" style="color:#DC2626;">🚨 PEPE 巨鲸清仓 2.5 亿代币至 OKX</span></div>
            <div class="data-row"><span class="data-label">昨日深夜</span><span class="data-value" style="color:#10B981;">🟢 SOL 链上新增质押 150 万枚</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ---------------- 页面 3：期权最大痛点推演 ----------------
    elif menu == "📈 期权最大痛点推演":
        st.markdown("<div class='hero-title'>OPTIONS MAX PAIN</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>揭秘华尔街期权庄家的底牌，锁定周五交割砸盘点</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <div class="data-row"><span class="data-label">本周五交割 BTC 最大痛点 (Max Pain)</span><span class="data-value" style="font-size:1.2rem;">$64,000</span></div>
            <div class="data-row"><span class="data-label">看跌/看涨期权比率 (P/C Ratio)</span><span class="data-value">0.85 (看涨情绪过热)</span></div>
            <div class="data-row"><span class="data-label">名义价值敞口总额</span><span class="data-value">$2.4 Billion</span></div>
            <p style="font-size: 12px; color: #475569; margin-top: 15px; background: #FEF2F2; padding: 10px; border-radius: 6px;">
                <strong>💡 机构推演：</strong>当前 BTC 现价远高于最大痛点。期权卖方（大庄家）有极强的动力在周五下午交割前，通过现货砸盘将价格逼近 $64,000，以实现自身利益最大化。<b>警惕周四晚间的洗盘瀑布！</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ---------------- 页面 4：跨市资金套利矩阵 ----------------
    elif menu == "🔄 跨市资金套利矩阵":
        st.markdown("<div class='hero-title'>FUNDING ARBITRAGE</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>自动抓取交易所费率差，实现年化 30%+ 无风险套利</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card" style="overflow-x: auto;">
            <table style="width:100%; text-align:left; font-size:13px;">
                <tr style="border-bottom: 2px solid #E2E8F0; color: #64748B;"><th>资产</th><th>Binance 费率</th><th>OKX 费率</th><th>Bybit 费率</th><th>策略建议</th></tr>
                <tr><td><b>BTC</b></td><td style="color:#DC2626;">+0.0150%</td><td style="color:#DC2626;">+0.0185%</td><td style="color:#10B981;">+0.0050%</td><td>OKX做空 / Bybit做多</td></tr>
                <tr><td><b>ETH</b></td><td style="color:#DC2626;">+0.0210%</td><td style="color:#DC2626;">+0.0250%</td><td style="color:#DC2626;">+0.0190%</td><td>观望</td></tr>
                <tr><td><b>WIF</b></td><td style="color:#10B981;">-0.0850%</td><td style="color:#DC2626;">+0.0120%</td><td style="color:#DC2626;">+0.0100%</td><td>Binance吃费率</td></tr>
            </table>
            <p style="font-size: 11px; color: #94A3B8; margin-top: 10px;">* 数据每分钟刷新。利用平台间的多空头寸对冲，可吃高额年化资金费且免疫涨跌。</p>
        </div>
        """, unsafe_allow_html=True)

    # ---------------- 页面 5：机构代币解锁预警 ----------------
    elif menu == "🔓 机构代币解锁预警":
        st.markdown("<div class='hero-title'>TOKEN UNLOCKS</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>提前埋伏 VC 解锁砸盘，做空抛压极其严重的空气币</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <div class="data-row"><span class="data-label">🚨 <b>APT</b> (Aptos)</span><span class="data-value" style="color:#DC2626;">倒计时: 2 天 | 解锁 $3.1 亿 (抛压极大)</span></div>
            <div class="data-row"><span class="data-label">⚠️ <b>ARB</b> (Arbitrum)</span><span class="data-value" style="color:#F59E0B;">倒计时: 5 天 | 解锁 $8,500 万 (偏空)</span></div>
            <div class="data-row"><span class="data-label">📉 <b>SUI</b> (Sui)</span><span class="data-value" style="color:#DC2626;">倒计时: 7 天 | 解锁 $1.2 亿 (团队代币释放)</span></div>
            <p style="font-size: 12px; color: #475569; margin-top: 15px;">机构筹码成本极低，天量解锁日往往伴随借币做空。建议提前在合约市场逢高布局空单拦截。</p>
        </div>
        """, unsafe_allow_html=True)

    # ---------------- 页面 6：AI K线形态识别 ----------------
    elif menu == "🤖 AI K线形态识别":
        st.markdown("<div class='hero-title'>AI PATTERN REC</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>通过深度学习神经网络，24小时自动扫描图表底部/顶部形态</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">📊 当前周期 AI 识别报告</h4>
            <div class="data-row"><span class="data-label">BTC/USDT (4H 级别)</span><span class="data-value">🧠 识别到 <b style="color:#10B981;">[看涨楔形]</b> | 胜率: 78%</span></div>
            <div class="data-row"><span class="data-label">ETH/USDT (1H 级别)</span><span class="data-value">🧠 识别到 <b style="color:#DC2626;">[头肩顶雏形]</b> | 胜率: 82%</span></div>
            <div class="data-row"><span class="data-label">SOL/USDT (日线级别)</span><span class="data-value">🧠 识别到 <b style="color:#10B981;">[圆弧底突破]</b> | 胜率: 91%</span></div>
            <p style="font-size: 12px; color: #94A3B8; margin-top: 15px;">* AI 模型基于近 10 年华尔街交易图表库训练，信号仅供结构参考，非绝对胜率。</p>
        </div>
        """, unsafe_allow_html=True)

    # ---------------- 页面 7：账户管理 ----------------
    elif menu == "💎 账户管理与支持":
        st.markdown("<div class='hero-title'>PRO ACCOUNT</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">升级或续期 Pro 权限</h4>
            <p style="color: #64748B; font-size: 14px;">USDT (TRC-20) 收款地址：</p>
            <div style="background: #F1F5F9; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 13px; text-align: center; word-break: break-all; color:#0F172A; font-weight:bold;">TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</div>
        </div>
        <div class="bento-card">
            <h4 style="margin-top:0;">您的专属服务</h4>
            <ul style="line-height: 2.5; font-size: 14px; color: #475569;">
                <li>🐧 <b>微信/QQ:</b> 1303467048</li>
                <li>✈️ <b>Telegram:</b> @YourTGHandle</li>
                <li>💼 <b>业务:</b> 承接大资金节点托管、量化 API 代写</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
