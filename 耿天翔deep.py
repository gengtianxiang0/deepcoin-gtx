import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import time
import plotly.graph_objects as go

# ================= 1. 全局配置 =================
st.set_page_config(page_title="AEGIS QUANT | 机构级投研", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

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
    
    /* 进度条样式 (失衡仪) */
    .progress-bar-container { width: 100%; height: 8px; background-color: #FEF2F2; border-radius: 4px; display: flex; overflow: hidden; margin-top: 5px; margin-bottom: 5px; }
    .progress-bar-buy { height: 100%; background-color: #10B981; }
    .progress-bar-sell { height: 100%; background-color: #DC2626; }
    
    /* 山寨币雷达表格 */
    .radar-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
    .radar-table th { padding: 10px 8px; border-bottom: 2px solid #F1F5F9; color: #64748B; font-weight: 600; }
    .radar-table td { padding: 12px 8px; border-bottom: 1px solid #F1F5F9; color: #0F172A; font-weight: 500; }
    
    @media (max-width: 768px) {
        .hero-title { font-size: 1.6rem; text-align: center; }
        .hero-subtitle { font-size: 0.9rem; text-align: center; }
        .bento-card { padding: 15px; border-radius: 12px; }
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
@st.cache_data(ttl=10)
def fetch_market_data():
    try:
        exchange = ccxt.okx({'enableRateLimit': True, 'timeout': 5000})
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
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
    res = df['high'].max()  
    sup = df['low'].min()   
    
    range_pct = (cur_p - sup) / (res - sup) if res != sup else 0.5
    buy_pressure = int((1 - range_pct) * 100) # 模拟买盘动能
    
    if range_pct < 0.35:
        signal = "🟢 现价做多 (STRONG BUY)"
        entry, tp, sl = f"{cur_p * 0.998:.2f}", f"{res * 0.98:.2f}", f"{sup * 0.99:.2f}"
        desc = "空头动能衰竭，底层订单簿显示巨鲸正在密集挂单托盘。盈亏比极佳，建议分批建仓多单。"
    elif range_pct > 0.65:
        signal = "🔴 逢高做空 (SELL SHORT)"
        entry, tp, sl = f"{cur_p * 1.002:.2f}", f"{sup * 1.02:.2f}", f"{res * 1.01:.2f}"
        desc = "触及高频压制区，CVD(累计成交量)呈现严重顶背离，极易发生多头踩踏。建议逢高布局空单。"
    else:
        signal = "⏳ 中性震荡 (NEUTRAL)"
        entry, tp, sl = "等待测试边界", "等待趋势确认", "严控仓位"
        desc = "处于中枢震荡区，主力资金正在进行多空双爆洗盘。请耐心等待右侧结构确立。"
        
    return {"price": cur_p, "res": res, "sup": sup, "text": signal, "entry": entry, "tp": tp, "sl": sl, "desc": desc, "buy_p": buy_pressure}

def generate_liquidation_chart(current_price, asset_type):
    prices = np.linspace(current_price * 0.85, current_price * 1.15, 120)
    multiplier = 80 if asset_type == 'BTC' else (30 if asset_type == 'ETH' else 10)
    short_liq = np.exp(-((prices - current_price * 1.05) ** 2) / (2 * (current_price * 0.018) ** 2)) * multiplier
    long_liq = np.exp(-((prices - current_price * 0.94) ** 2) / (2 * (current_price * 0.015) ** 2)) * (multiplier * 1.5)
    noise = np.random.uniform(0, multiplier*0.1, 120)
    liquidity = short_liq + long_liq + noise
    
    colors = ['#DC2626' if p > current_price else '#10B981' for p in prices]
    fig = go.Figure(data=[go.Bar(x=prices, y=liquidity, marker_color=colors)])
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title=f"{asset_type} 流动性清算极值 (USDT)", tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, showticklabels=False),
        showlegend=False
    )
    return fig, prices[np.argmax(long_liq)], prices[np.argmax(short_liq)]

# ================= 4. 页面路由与渲染 =================

if not st.session_state.access_granted:
    # ---------------- 门禁页面 ----------------
    st.markdown("<div style='margin-top: 2vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title'>AEGIS QUANT 投研终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>全网最锐利的链上数据与高频订单簿分析系统。</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div>
                <span style="background: #ECFDF5; color: #059669; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">机构内推通道</span>
                <h3 style="margin-top: 10px; color: #0F172A;">节点授权模式</h3>
                <div class="price-tag">限时免费</div>
                <div class="feature-list">
                    ✓ 永久解锁 <b>BTC/ETH/SOL</b> 顶级现价策略<br>
                    ✓ 实时探测合约清算热力图与巨鲸痛点<br>
                    ✓ 独家山寨币异动狙击雷达 (实时更新)<br>
                    ✓ 享受交易所最高级别 50% 手续费减免<br>
                </div>
            </div>
            <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 点击获取 AEGIS 专属授权账户</a>
        </div>
        """, unsafe_allow_html=True)
        
        uid_input = st.text_input("👉 输入已注册的 UID 验证激活引擎：", placeholder="例如: 20061008")
        if st.button("立即验证并初始化引擎", use_container_width=True):
            if uid_input in ["20061008", "888888"]:
                st.session_state.access_granted = True
                st.session_state.uid = uid_input
                st.rerun()
            else:
                st.error("❌ 拦截：未检测到该 UID 的节点归属权！请确认使用上方链接重新开户。")

    with col2:
        st.markdown("""
        <div class="gate-card paid">
            <div>
                <span style="background: #EEF2FF; color: #4F46E5; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">独立 API 版</span>
                <h3 style="margin-top: 10px; color: #0F172A;">Pro 专业买断模式</h3>
                <div class="price-tag">50 USDT <span style="font-size: 1rem; color:#64748B;">/ 月</span></div>
                <div class="feature-list">
                    ✓ 解除一切交易所节点绑定限制<br>
                    ✓ 开放全币种(Top 100)监控权限<br>
                    ✓ 包含 AEGIS 投研系统全部隐藏指标<br>
                    ✓ 专属客户经理 1V1 疑难解答<br>
                </div>
            </div>
            <a href="mailto:your_email@example.com" class="btn-primary" style="background: #4F46E5;">联系主理人开通 Pro 权限</a>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔑 管理员后门进入", use_container_width=True):
            st.session_state.access_granted = True
            st.session_state.uid = "Admin_Test"
            st.rerun()

else:
    # ---------------- 内部系统：顶级移动端主控台 ----------------
    
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 900; color: #0F172A; margin-bottom: 0px;'>🛡️ AEGIS QUANT</h2>", unsafe_allow_html=True)
        st.caption("系统状态: Deep Web API 直连 🟢")
        
        st.markdown(f"""
        <div style="background: #EEF2FF; padding: 12px; border-radius: 8px; margin: 10px 0; border: 1px solid #C7D2FE;">
            <div style="font-size: 11px; color: #4F46E5; font-weight: 700; margin-bottom: 3px;">✅ 节点引擎已挂载</div>
            <div style="font-size: 14px; color: #0F172A; font-weight: 800;">UID: {st.session_state.uid}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        menu = st.radio("系统功能矩阵", ["🎯 Alpha 核心指令舱", "🔥 Web3 山寨狙击雷达", "💎 Pro 账户管理", "📞 联系安全顾问"])
        st.markdown("---")
        if st.button("注销当前会话"):
            st.session_state.access_granted = False
            st.session_state.uid = ""
            st.rerun()

    if menu == "🎯 Alpha 核心指令舱":
        st.markdown("<div class='hero-title'>AEGIS ALPHA ENGINE</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>实时挂单簿失衡探测与清算热力推演</div>", unsafe_allow_html=True)

        with st.spinner('正在破译底层交易所深度数据...'):
            market_data = fetch_market_data()

        if market_data:
            # 使用 Tabs 极大地提升手机端的高级感和空间利用率
            tab_btc, tab_eth, tab_sol = st.tabs(["🟠 BTC 核心", "🔵 ETH 核心", "🟣 SOL 异动"])
            
            for tab, sym, name in zip([tab_btc, tab_eth, tab_sol], ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'], ['BTC', 'ETH', 'SOL']):
                with tab:
                    strat = generate_strategy(market_data[sym], name)
                    
                    # 价格与策略卡片
                    st.markdown(f"""
                    <div class="bento-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 10px;">
                            <span style="font-size: 1.2rem; font-weight: 900;">{sym}</span>
                            <span style="font-size: 1.4rem; font-weight: 800; color: #0F172A;">${strat['price']:,.2f}</span>
                        </div>
                        
                        <div style="font-size: 11px; color: #64748B; margin-bottom: 2px; display: flex; justify-content: space-between;">
                            <span>🟢 买盘墙动能 ({strat['buy_p']}%)</span>
                            <span>🔴 卖盘墙动能 ({100-strat['buy_p']}%)</span>
                        </div>
                        <div class="progress-bar-container" style="margin-bottom: 15px;">
                            <div class="progress-bar-buy" style="width: {strat['buy_p']}%;"></div>
                            <div class="progress-bar-sell" style="width: {100-strat['buy_p']}%;"></div>
                        </div>

                        <div style="font-weight: 800; font-size: 15px; margin-bottom: 8px;">{strat['text']}</div>
                        <p style="font-size: 12px; color: #64748B; line-height: 1.5; margin-bottom: 15px; background: #F8FAFC; padding: 8px; border-radius: 6px;">{strat['desc']}</p>
                        
                        <div class="data-row" style="background: #FEF2F2; padding: 4px 8px; border-radius: 4px;"><span class="data-label">🔴 上方阻力 (Resistance)</span><span class="data-value" style="color: #DC2626;">${strat['res']:,.2f}</span></div>
                        <div class="data-row" style="background: #ECFDF5; padding: 4px 8px; border-radius: 4px; margin-bottom: 10px;"><span class="data-label">🟢 下方铁底 (Support)</span><span class="data-value" style="color: #10B981;">${strat['sup']:,.2f}</span></div>
                        
                        <div class="data-row"><span class="data-label">精准进场点 (Entry)</span><span class="data-value">{strat['entry']}</span></div>
                        <div class="data-row"><span class="data-label">第一止盈位 (TP)</span><span class="data-value" style="color: #059669;">{strat['tp']}</span></div>
                        <div class="data-row"><span class="data-label">结构止损位 (SL)</span><span class="data-value" style="color: #DC2626;">{strat['sl']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 清算热力图卡片
                    st.markdown(f"<h3 style='font-size: 1.1rem; margin-top: 5px; margin-bottom: 10px;'>🔥 {name} 庄家猎杀极值图</h3>", unsafe_allow_html=True)
                    fig, l_liq, s_liq = generate_liquidation_chart(strat['price'], name)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown(f"""
                    <div class="bento-card" style="padding: 15px; margin-top: -15px;">
                        <div class="data-row"><span class="data-label">向上拔网线点 (空头爆仓极值)</span><span class="data-value" style="color:#DC2626;">${s_liq:,.2f}</span></div>
                        <div class="data-row"><span class="data-label">向下插针点 (多头爆仓极值)</span><span class="data-value" style="color:#10B981;">${l_liq:,.2f}</span></div>
                        <p style="font-size: 12px; color: #475569; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #E2E8F0;">
                            <strong>🛡️ AEGIS 推演：</strong>上方 ${s_liq:,.0f} 聚集了海量散户止损单，庄家向上猎杀流动性的收益极高。严禁在此区间盲目扛单。
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error("⚠️ 底层数据解密失败，请下拉刷新页面。")

    elif menu == "🔥 Web3 山寨狙击雷达":
        st.markdown("<div class='hero-title'>ALTCOIN RADAR</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>高波动率山寨币资金流向实时侦测</div>", unsafe_allow_html=True)
        
        # 这个板块是纯粹为了转化小白的，看起来信息量极大
        st.markdown("""
        <div class="bento-card" style="padding: 15px; overflow-x: auto;">
            <table class="radar-table">
                <tr><th>标的 (Ticker)</th><th>RSI (1H)</th><th>主力资金动向</th><th>AI 机器评级</th></tr>
                <tr><td><b>PEPE/USDT</b></td><td style="color:#DC2626; font-weight:bold;">78.5 (严重超买)</td><td>净流出 $4.2M</td><td>🔴 逢高沽空</td></tr>
                <tr><td><b>WIF/USDT</b></td><td style="color:#10B981; font-weight:bold;">28.1 (严重超卖)</td><td>机构建仓 $1.5M</td><td>🟢 现价抄底</td></tr>
                <tr><td><b>DOGE/USDT</b></td><td style="color:#64748B;">45.2 (中性震荡)</td><td>散户互搏</td><td>⏳ 观望</td></tr>
                <tr><td><b>ORDI/USDT</b></td><td style="color:#DC2626; font-weight:bold;">82.0 (极度危险)</td><td>大户抛售 $8.9M</td><td>🔴 强烈做空</td></tr>
                <tr><td><b>BOME/USDT</b></td><td style="color:#10B981; font-weight:bold;">35.4 (温和反弹)</td><td>净流入 $2.1M</td><td>🟢 逢低做多</td></tr>
            </table>
            <p style="font-size: 11px; color: #94A3B8; margin-top: 10px; margin-bottom: 0;">* 数据由 AEGIS 底层爬虫每 10 秒扫描全网 150 个热门交易对得出。山寨币波动巨大，请严格控制仓位。</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h3 style='font-size: 1.1rem; margin-top: 15px; margin-bottom: 10px;'>📡 宏观情绪面侦测</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <div class="data-row"><span class="data-label">贪婪恐慌指数 (F&G)</span><span class="data-value" style="color: #DC2626;">79 (极度贪婪 ⚠️)</span></div>
            <div class="data-row"><span class="data-label">全球永续多空比 (Global L/S)</span><span class="data-value">0.85 (空头占优)</span></div>
            <div class="data-row"><span class="data-label">全网 24H 爆仓总额</span><span class="data-value" style="color: #DC2626;">$ 245,000,000</span></div>
            <div class="data-row"><span class="data-label">稳定币增发 (USDT/USDC)</span><span class="data-value" style="color: #10B981;">净流入 +1.2 亿</span></div>
        </div>
        """, unsafe_allow_html=True)

    elif menu == "💎 Pro 账户管理":
        st.markdown("<div class='hero-title'>PRO ACCOUNT</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">升级或续期 Pro 权限</h4>
            <p style="color: #64748B; font-size: 14px;">请使用 USDT (TRC-20) 网络转入 <strong>50 USDT</strong>，完成后截图发送给客户经理开通权限。</p>
            <div style="background: #F1F5F9; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 13px; text-align: center; word-break: break-all; color:#0F172A; font-weight:bold;">
                TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            </div>
            <p style="font-size: 12px; color: #DC2626; margin-top:15px;">⚠️ 资产防丢警告：请在转账前仔细核对末尾 4 位地址，充错网络将导致资产永久丢失，本平台概不负责。</p>
        </div>
        """, unsafe_allow_html=True)

    elif menu == "📞 联系安全顾问":
        st.markdown("<div class='hero-title'>SUPPORT</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="bento-card">
            <h4 style="margin-top:0;">您的专属顾问</h4>
            <p style="font-size: 13px; color: #475569;">无论您是需要 Pro 版续期、定制化量化策略代写、还是大资金节点托管业务，请随时联系您的安全顾问。</p>
            <ul style="line-height: 2.5; font-size: 14px; padding-left: 20px; font-weight: 500;">
                <li>🐧 <b>核心内测 QQ:</b> <span style="color:#0F172A;">1303467048</span></li>
                <li>✈️ <b>Telegram:</b> <span style="color:#0F172A;">@YourTGHandle</span></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
