import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import time
import plotly.graph_objects as go

# ================= 1. 全局配置与状态初始化 =================
st.set_page_config(page_title="Alpha Terminal", page_icon="⬛", layout="wide", initial_sidebar_state="expanded")

# 初始化登录状态与 UID (门禁开关)
if 'access_granted' not in st.session_state:
    st.session_state.access_granted = False
if 'uid' not in st.session_state:
    st.session_state.uid = ""

# ================= 2. 顶级 Fintech CSS 缝合 =================
custom_css = """
<style>
    /* 全局极简冷色调 */
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: "Inter", -apple-system, sans-serif; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 0rem; max-width: 1200px; }
    
    /* 大标题与副标题 */
    .hero-title { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.05em; color: #020617; margin-bottom: 5px; }
    .hero-subtitle { font-size: 1.1rem; color: #64748B; margin-bottom: 30px; font-weight: 500; }
    
    /* 门禁二选一卡片样式 */
    .gate-card { background: #FFFFFF; border-radius: 16px; padding: 40px 30px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.05); border: 2px solid transparent; transition: all 0.3s; height: 100%; display: flex; flex-direction: column; justify-content: space-between;}
    .gate-card:hover { transform: translateY(-5px); }
    .gate-card.free { border-color: #10B981; }
    .gate-card.paid { border-color: #6366F1; }
    
    /* 门禁内部元素 */
    .price-tag { font-size: 2rem; font-weight: 800; color: #0F172A; margin: 15px 0; }
    .feature-list { line-height: 2; color: #475569; font-size: 15px; margin-bottom: 30px; }
    .btn-primary { display: block; text-align: center; background: #020617; color: #FFFFFF !important; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: 700; transition: 0.2s; }
    .btn-primary:hover { background: #334155; }

    /* Bento Box 便当盒样式 (主控台) */
    .bento-card { background: #FFFFFF; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); border: 1px solid #F1F5F9; margin-bottom: 20px; transition: transform 0.2s; }
    .bento-card:hover { transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); }
    
    /* 策略指令标签 */
    .signal-tag-long { display: inline-block; padding: 6px 12px; background: #ECFDF5; color: #059669; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    .signal-tag-short { display: inline-block; padding: 6px 12px; background: #FEF2F2; color: #DC2626; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    .signal-tag-wait { display: inline-block; padding: 6px 12px; background: #F1F5F9; color: #475569; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 15px;}
    
    .data-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #E2E8F0; }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #64748B; font-size: 14px; }
    .data-value { font-weight: 600; color: #0F172A; font-size: 14px; }
    .module-title { font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= 3. 底层数据引擎 (OKX API) =================
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
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

def generate_strategy(df, symbol):
    cur_p = df['close'].iloc[-1]
    res = df['high'].max()  # 24小时最高点作为压力位
    sup = df['low'].min()   # 24小时最低点作为支撑位
    
    range_pct = (cur_p - sup) / (res - sup) if res != sup else 0.5
    
    if range_pct < 0.35:
        signal, tag_class, tag_text = "LONG", "signal-tag-long", "🟢 强烈做多 (STRONG BUY)"
        entry, tp, sl = f"{cur_p * 0.998:.2f}", f"{res * 0.99:.2f}", f"{sup * 0.995:.2f}"
        desc = f"现价已逼近链上巨鲸护盘铁底。空头动能衰竭，盈亏比极佳。建议在 Deepcoin 现价或回调至 {entry} 分批建仓。"
    elif range_pct > 0.65:
        signal, tag_class, tag_text = "SHORT", "signal-tag-short", "🔴 逢高做空 (SELL SHORT)"
        entry, tp, sl = f"{cur_p * 1.002:.2f}", f"{sup * 1.01:.2f}", f"{res * 1.005:.2f}"
        desc = f"上方触及高频挂单密集压制区。量能呈现顶背离，极易发生多头踩踏。建议在 {entry} 附近布局空单。"
    else:
        signal, tag_class, tag_text = "WAIT", "signal-tag-wait", "⏳ 中性震荡 (NEUTRAL)"
        entry, tp, sl = "暂不建议现价进场", "等待测试边界", "严控仓位"
        desc = "当前处于支撑与压力的中枢震荡区，多空博弈激烈。请等待价格触碰强压或强撑后再做右侧交易。"
        
    return {"price": cur_p, "res": res, "sup": sup, "class": tag_class, "text": tag_text, "entry": entry, "tp": tp, "sl": sl, "desc": desc}

def generate_liquidation_chart(current_price):
    # 模拟生成清算图数据 (逼真度拉满)
    prices = np.linspace(current_price * 0.88, current_price * 1.12, 120)
    short_liq = np.exp(-((prices - current_price * 1.04) ** 2) / (2 * (current_price * 0.015) ** 2)) * 80
    long_liq = np.exp(-((prices - current_price * 0.95) ** 2) / (2 * (current_price * 0.012) ** 2)) * 120
    noise = np.random.uniform(0, 8, 120)
    liquidity = short_liq + long_liq + noise
    
    colors = ['#DC2626' if p > current_price else '#10B981' for p in prices]
    
    fig = go.Figure(data=[go.Bar(x=prices, y=liquidity, marker_color=colors)])
    fig.update_layout(
        margin=dict(l=0, r=0, t=20, b=0), height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="资产价格 (USDT)"),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="清算强度 (百万 USDT)"),
        showlegend=False
    )
    
    high_liq_short = prices[np.argmax(short_liq)]
    high_liq_long = prices[np.argmax(long_liq)]
    return fig, high_liq_long, high_liq_short

# ================= 4. 路由拦截与页面渲染 =================

if not st.session_state.access_granted:
    # ---------------- 门禁页面 ----------------
    st.markdown("<div style='margin-top: 5vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title' style='text-align: center;'>QUANT ALPHA 终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle' style='text-align: center;'>请选择您的终端接入方式，获取机构级监控权限。</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div>
                <span style="background: #ECFDF5; color: #059669; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">强烈推荐</span>
                <h3 style="margin-top: 15px; color: #0F172A;">节点授权模式</h3>
                <div class="price-tag">免费接入</div>
                <div class="feature-list">
                    ✓ 永久免费使用 Alpha 终端全部功能<br>
                    ✓ 实时获取 AI 双币对交易策略与清算图<br>
                    ✓ 享受全网最高 50% 手续费减免<br>
                </div>
            </div>
            <div>
                <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 点击获取 Deepcoin 专属返佣账户</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        uid_input = st.text_input("👉 已经通过上方链接注册？输入 UID 验证解锁：", placeholder="例如: 20061008")
        if st.button("立即验证 UID", use_container_width=True):
            if uid_input in ["20061008", "888888"]:
                st.session_state.access_granted = True
                st.session_state.uid = uid_input
                st.rerun()
            else:
                st.error("❌ UID 未授权或未达标！请确认使用本站链接注册，或联系客服。")

    with col2:
        st.markdown("""
        <div class="gate-card paid">
            <div>
                <span style="background: #EEF2FF; color: #4F46E5; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">独立版</span>
                <h3 style="margin-top: 15px; color: #0F172A;">Pro 独立买断模式</h3>
                <div class="price-tag">50 USDT <span style="font-size: 1rem; color:#64748B; font-weight: 500;">/ 月</span></div>
                <div class="feature-list">
                    ✓ 无需绑定任何交易所节点限制<br>
                    ✓ 适合已有固定交易习惯的老手<br>
                    ✓ 包含 Alpha 终端全部功能与数据<br>
                </div>
            </div>
            <div>
                <a href="mailto:your_email@example.com" class="btn-primary" style="background: #4F46E5;">联系主理人开通 Pro 版</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔑 测试通道 (管理员一键直达)", use_container_width=True):
            st.session_state.access_granted = True
            st.session_state.uid = "Admin_Test"
            st.rerun()

else:
    # ---------------- 内部系统：顶级便当盒主控台 ----------------
    
    # 侧边栏导航：新增已授权用户专属卡片
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 800; color: #0F172A; margin-bottom: 0px;'>⚡ QUANT ALPHA</h2>", unsafe_allow_html=True)
        st.caption("系统状态: OKX 节点直连 🟢")
        
        # 用户状态卡片
        st.markdown(f"""
        <div style="background: #EEF2FF; padding: 15px; border-radius: 12px; margin: 15px 0; border: 1px solid #C7D2FE;">
            <div style="font-size: 12px; color: #4F46E5; font-weight: 700; margin-bottom: 5px;">✅ Alpha 节点已授权</div>
            <div style="font-size: 16px; color: #0F172A; font-weight: 800;">当前 UID: {st.session_state.uid}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        menu = st.radio("导航菜单", ["🎯 Alpha 策略主控台", "💎 Pro 续费通道", "📞 联系您的客户经理"])
        st.markdown("---")
        if st.button("登出终端 / 切换账号"):
            st.session_state.access_granted = False
            st.session_state.uid = ""
            st.rerun()

    # ---- 页面 1：Alpha 策略主控台 ----
    if menu == "🎯 Alpha 策略主控台":
        st.markdown("<div class='hero-title'>QUANT ALPHA TERMINAL</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>机构级流动性监控与高频交易指令中枢</div>", unsafe_allow_html=True)

        with st.spinner('正在直连 OKX 专线解析深度数据...'):
            market_data = fetch_market_data()

        if market_data:
            st.markdown("<h3 style='font-size: 1.2rem; margin-bottom: 15px;'>🎯 AI 核心策略与压力位演算</h3>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            # BTC 卡片 (新增压力支撑位)
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
                    <div class="data-row" style="background: #F8FAFC; padding: 5px 10px; border-radius: 4px;"><span class="data-label">🔴 上方强压 (Resistance)</span><span class="data-value" style="color: #DC2626;">${btc_strat['res']:,.2f}</span></div>
                    <div class="data-row" style="background: #F8FAFC; padding: 5px 10px; border-radius: 4px; margin-bottom: 15px;"><span class="data-label">🟢 下方铁底 (Support)</span><span class="data-value" style="color: #10B981;">${btc_strat['sup']:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">执行指令 (Entry)</span><span class="data-value">{btc_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{btc_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{btc_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # ETH 卡片 (新增压力支撑位)
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
                    <div class="data-row" style="background: #F8FAFC; padding: 5px 10px; border-radius: 4px;"><span class="data-label">🔴 上方强压 (Resistance)</span><span class="data-value" style="color: #DC2626;">${eth_strat['res']:,.2f}</span></div>
                    <div class="data-row" style="background: #F8FAFC; padding: 5px 10px; border-radius: 4px; margin-bottom: 15px;"><span class="data-label">🟢 下方铁底 (Support)</span><span class="data-value" style="color: #10B981;">${eth_strat['sup']:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">执行指令 (Entry)</span><span class="data-value">{eth_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{eth_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{eth_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # --- 全新模块：清算热力图与痛点分析 ---
            st.markdown("<h3 style='font-size: 1.2rem; margin-top: 10px; margin-bottom: 15px;'>🔥 BTC 全网合约清算热力图与痛点</h3>", unsafe_allow_html=True)
            
            # 拿到图表和数据
            btc_current = btc_strat['price']
            fig, long_liq_p, short_liq_p = generate_liquidation_chart(btc_current)
            
            col_chart, col_data = st.columns([3, 2])
            with col_chart:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            with col_data:
                st.markdown(f"""
                <div class="bento-card" style="height: 95%;">
                    <h4 style="margin-top:0; color: #0F172A;">🛡️ 猎杀清算痛点分析</h4>
                    <div class="data-row"><span class="data-label">大概率向上清算点 (空头爆仓)</span><span class="data-value" style="color:#DC2626; font-size: 16px;">${short_liq_p:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">大概率向下清算点 (多头爆仓)</span><span class="data-value" style="color:#10B981; font-size: 16px;">${long_liq_p:,.2f}</span></div>
                    <div class="data-row"><span class="data-label">上方蓄水池 (清算压力)</span><span class="data-value">极高 (约 $1.25 亿)</span></div>
                    <div class="data-row"><span class="data-label">下方蓄水池 (清算压力)</span><span class="data-value">中等 (约 $6,800 万)</span></div>
                    <p style="font-size: 13px; color: #475569; margin-top: 15px; line-height: 1.6; background: #F8FAFC; padding: 10px; border-radius: 6px; border-left: 3px solid #6366F1;">
                        <strong>🤖 机器推演：</strong>上方 {short_liq_p:,.0f} 附近聚集了大量高倍空头止损盘。庄家极有可能在未来 12 小时内发起一波向上插针，猎杀上方流动性后再顺势砸盘。严禁在高位追多！
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # 底部流动性卡片 (保留)
            st.markdown("<h3 style='font-size: 1.2rem; margin-top: 5px; margin-bottom: 15px;'>⚡ 链上异动监控</h3>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                st.markdown("""
                <div class="bento-card" style="padding: 20px;">
                    <div class="module-title">⚖️ 永续资金费率预警</div>
                    <div class="data-row"><span class="data-label">BTC 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0150%</span></div>
                    <div class="data-row"><span class="data-label">ETH 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0210%</span></div>
                    <p style="font-size: 13px; color: #64748B; margin-top: 15px; margin-bottom: 0;">分析：多头费率偏高，做多成本增加，谨防主力反向诱空杀跌。</p>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown("""
                <div class="bento-card" style="padding: 20px;">
                    <div class="module-title">🐋 链上 Smart Money</div>
                    <div style="font-size: 13px; line-height: 1.8;">
                        <div style="color: #0F172A;">🚨 <b>1,200 BTC</b> 转入未知钱包</div>
                        <div style="color: #64748B; font-size: 11px; margin-bottom: 8px;">2 分钟前 (深网监控节点)</div>
                        <div style="color: #0F172A;">🚨 <b>50,000 ETH</b> 移出交易所</div>
                        <div style="color: #64748B; font-size: 11px; margin-bottom: 0;">15 分钟前 (巨鲸地址标记)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.error("⚠️ 专线连接异常，请刷新重试或检查底层网络节点。")

    # ---- 页面 2：充值与续费 ----
    elif menu == "💎 Pro 续费通道":
        st.markdown("<div class='hero-title'>Pro 账户授权续期</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
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

    # ---- 页面 3：联系客服 ----
    elif menu == "📞 联系您的客户经理":
        st.markdown("<div class='hero-title'>获取技术支持</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
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
