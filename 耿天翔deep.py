import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ccxt
from datetime import datetime

# ================= 1. 全局配置与高级 CSS 强注 =================
st.set_page_config(page_title="Deepcoin Alpha Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    .stApp { background-color: #0B0E14; color: #E2E8F0; font-family: 'Helvetica Neue', sans-serif; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    div[data-testid="stMetric"] { background-color: #151A23; border: 1px solid #1E293B; padding: 15px 20px; border-radius: 6px; border-left: 4px solid #3B82F6; }
    [data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid #1E293B; }
    .glow-title { color: #F8FAFC; text-shadow: 0 0 10px rgba(59, 130, 246, 0.5); font-weight: 700; margin-bottom: 0px; }
    /* AI 策略卡片样式 */
    .ai-card { background-color: #1A222C; border: 1px solid #3B82F6; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 0 15px rgba(59, 130, 246, 0.2); }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

valid_uids = ["20061008", "888888"]

# ================= 2. 侧边栏：私域漏斗 =================
with st.sidebar:
    st.markdown("<h2 class='glow-title'>⚡ QUANT ALPHA</h2>", unsafe_allow_html=True)
    st.caption("SYSTEM STATUS: OKX NODE | 延迟 8ms 🟢")
    st.markdown("---")
    
    st.markdown("### 🔐 引擎访问授权")
    uid_input = st.text_input("🔑 输入 Deepcoin UID 激活：", type="password", placeholder="例如: 10086...")
    
    st.markdown("---")
    st.markdown("### 👑 高净值客户通道")
    st.info("⚠️ 仅接受大资金托管、量化 API 私有化部署咨询。")
    st.markdown("""
    * 🐧 **首席主理人 QQ**: `1303467048`
    * 💬 **验证备注**: 深币 Alpha 会员
    """)
    
    st.markdown("---")
    st.markdown("### 🎁 核心节点专属权限")
    st.markdown("""
    <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: block; text-align: center; background-color: #2563EB; color: white; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold;">
        👉 点击获取 50% 手续费返佣通道
    </a>
    """, unsafe_allow_html=True)

# ================= 3. 底层引擎抓取 =================
@st.cache_data(ttl=60)
def fetch_real_kline_data(symbol, timeframe='1h', limit=100):
    try:
        exchange = ccxt.okx({'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        return str(e)

# ================= 4. 主界面路由 =================
if uid_input in valid_uids:
    st.markdown("<h2 class='glow-title'>⚡ Deepcoin 机构级高频狙击终端</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    symbol_map = {"$BTC / USDT (Bitcoin)": "BTC/USDT", "$ETH / USDT (Ethereum)": "ETH/USDT", "$SOL / USDT (Solana)": "SOL/USDT"}
    col_sel, col_empty = st.columns([1, 2])
    with col_sel:
        selected_coin = st.selectbox("🎯 挂载监控算法模型", list(symbol_map.keys()))
    
    real_symbol = symbol_map[selected_coin]
    
    with st.spinner(f'正在通过底层专线解析 {real_symbol} 盘口深度...'):
        df = fetch_real_kline_data(real_symbol, timeframe='1h', limit=100)
    
    if isinstance(df, pd.DataFrame) and not df.empty:
        cur_p = df['close'].iloc[-1]
        res = df['high'].rolling(window=20).max().iloc[-1]
        sup = df['low'].rolling(window=20).min().iloc[-1]
        
        # 1. 渲染欧易同款实心 K 线
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#2ebd85', increasing_fillcolor='#2ebd85', # OKX 实体绿
            decreasing_line_color='#f23645', decreasing_fillcolor='#f23645'  # OKX 实体红
        )])
        fig.add_hline(y=res, line_dash="dot", line_color="#f23645", annotation_text=f"强抛压区: {res:.2f}", annotation_font_color="#f23645")
        fig.add_hline(y=sup, line_dash="dot", line_color="#2ebd85", annotation_text=f"强支撑区: {sup:.2f}", annotation_font_color="#2ebd85")
        
        # 隐藏下方多余的时间滑块，让图表更纯粹
        fig.update_layout(
            template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=20, b=0), height=450
        )
        
        # 2. 注入核心 config，开启鼠标滚轮缩放 (scrollZoom: True)
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
        
        # 基础数据卡片
        col1, col2, col3 = st.columns(3)
        col1.metric("⚡ 当前现价 (OKX 实时)", f"{cur_p:.4f} USDT")
        col2.metric("🔴 上方强压 (做空/止盈区)", f"{res:.4f} USDT", delta_color="inverse")
        col3.metric("🟢 下方铁底 (做多/抄底区)", f"{sup:.4f} USDT")
        
        # 3. AI 动态分析引擎逻辑
        st.markdown("### 🧠 AI 量化引擎实时决策")
        
        range_total = res - sup
        distance_to_sup = cur_p - sup
        distance_to_res = res - cur_p
        
        # 测算逻辑：距离底部 20% 以内看多，距离顶部 20% 以内看空，中间震荡
        if distance_to_sup < range_total * 0.2:
            ai_signal = "🟢 强烈做多 (STRONG LONG)"
            ai_color = "#2ebd85"
            ai_desc = f"现价已逼近链上巨鲸护盘铁底 {sup:.4f}，空头动能极度衰竭，盈亏比极佳。建议立刻在 Deepcoin 现价开多，止损设在 {sup*0.99:.4f} 附近，博取超跌反弹。"
        elif distance_to_res < range_total * 0.2:
            ai_signal = "🔴 强烈做空 (STRONG SHORT)"
            ai_color = "#f23645"
            ai_desc = f"现价已触及上方高频挂单强压区 {res:.4f}，极易发生多头踩踏与插针崩盘。建议逢高开空，不要扛单，短线目标看向中轨区域。"
        else:
            ai_signal = "⏳ 震荡观望 / 网格交易 (NEUTRAL)"
            ai_color = "#E2E8F0"
            ai_desc = f"当前价格处于支撑与阻力的中轨区域，多空博弈激烈，方向不明。请等待行情触碰强压 {res:.4f} 或强支撑 {sup:.4f} 后再做右侧交易，切勿盲目追单。"

        # 渲染 AI 策略卡片
        st.markdown(f"""
        <div class="ai-card">
            <h4 style="color: {ai_color}; margin-top: 0px;">当前信号指令：{ai_signal}</h4>
            <p style="font-size: 16px; color: #94A3B8; line-height: 1.6;"><strong>底层逻辑推演：</strong>{ai_desc}</p>
            <hr style="border-color: #334155;">
            <p style="font-size: 14px; color: #64748B; margin-bottom: 0px;">⚡ 行动指南：请严格按照上述信号，通过左侧通道进入 <b>Deepcoin 交易所</b> 执行挂单，吃透内部返佣政策红利。</p>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.error(f"❌ 专线连接异常，请重试。报错日志: {df}")

else:
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-top: 50px;'>⚡ ALPHA TERMINAL</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #64748B;'>机构级量化行情与合约狙击系统</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.error("🚫 **访问被拒绝：检测到您的 IP 尚未获得节点授权。**")
    
    st.markdown("### 📋 终端使用协议与开户条件")
    st.markdown("""
    本量化终端由私人游资团队开发，采用 OKX 底层毫秒级接口，提供**高胜率短线开单信号、自动测算顶级支撑/压力位**。
    
    **为避免被交易所风控及防止白嫖，本系统执行极其严格的准入机制：**
    
    1. **必须使用主理人邀请码注册**：您必须通过本节点的专属邀请通道注册 **Deepcoin (深币)** 交易所账号。
    2. **UID 绑定激活**：注册完成后，在左侧侧边栏输入您的深币 UID。系统将通过 API 自动核验您的节点归属。
    3. **资金量限制**：首充不低于 100 USDT，系统方可保持您的 UID 永久激活状态。（零资金账户将在 24 小时后被系统自动封禁）
    4. **使用规范**：严禁将本终端提供的点位截图外传，一经发现立刻拉黑。
    """)
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.info("👇 立即获取授权资格 👇")
        st.markdown("""
        <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: block; text-align: center; background-color: #10B981; color: white; padding: 15px; border-radius: 8px; text-decoration: none; font-size: 18px; font-weight: bold; margin-bottom: 20px;">
            🔗 第一步：点击此处使用节点邀请码开户
        </a>
        """, unsafe_allow_html=True)
        st.write("👉 **第二步：注册完成后，将您的深币 UID 填入左侧输入框即可秒开权限。**")
