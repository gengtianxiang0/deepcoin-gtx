import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ccxt
from datetime import datetime

# ================= 1. 全局配置与极简白 CSS =================
st.set_page_config(page_title="Deepcoin Alpha", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# 强制注入极简白色主题 CSS
custom_css = """
<style>
    /* 全局纯白背景与深灰黑字体，苹果极简风 */
    .stApp { background-color: #FFFFFF; color: #1E293B; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    /* 隐藏官方水印 */
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 数据卡片：浅灰底色，极简边框，去除花里胡哨的阴影 */
    div[data-testid="stMetric"] { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px 20px; border-radius: 8px; border-left: 4px solid #3B82F6; box-shadow: none; }
    
    /* 侧边栏：极浅灰区分层级 */
    [data-testid="stSidebar"] { background-color: #F1F5F9; border-right: 1px solid #E2E8F0; }
    
    /* 标题：干净利落的纯黑粗体 */
    .clean-title { color: #0F172A; font-weight: 800; font-size: 2rem; margin-bottom: 10px; }
    
    /* AI 策略卡片：干净的白底灰框 */
    .ai-card { background-color: #FFFFFF; border: 1px solid #CBD5E1; padding: 20px; border-radius: 8px; margin-top: 20px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

valid_uids = ["20061008", "888888"]

# ================= 2. 侧边栏：私域漏斗 (干净版) =================
with st.sidebar:
    st.markdown("<div class='clean-title'>📊 QUANT ALPHA</div>", unsafe_allow_html=True)
    st.caption("系统状态: OKX 节点直连 | 🟢 运行中")
    st.markdown("---")
    
    st.markdown("### 🔐 访问授权")
    uid_input = st.text_input("🔑 输入 Deepcoin UID：", type="password", placeholder="例如: 10086...")
    
    st.markdown("---")
    st.markdown("### 👑 VIP 咨询")
    st.info("大资金托管、API 私有化部署")
    st.markdown("""
    * 🐧 **专属 QQ**: `1303467048`
    * 💬 **备注**: 深币 Alpha
    """)
    
    st.markdown("---")
    st.markdown("### 🎁 专属开户通道")
    st.markdown("""
    <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: block; text-align: center; background-color: #0F172A; color: white; padding: 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px;">
        👉 获取 50% 手续费减免
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
    st.markdown("<div class='clean-title'>机构级高频监控终端</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    symbol_map = {"BTC / USDT (比特币)": "BTC/USDT", "ETH / USDT (以太坊)": "ETH/USDT", "SOL / USDT (索拉纳)": "SOL/USDT"}
    col_sel, col_empty = st.columns([1, 2])
    with col_sel:
        selected_coin = st.selectbox("选择监控标的", list(symbol_map.keys()))
    
    real_symbol = symbol_map[selected_coin]
    
    with st.spinner(f'正在解析 {real_symbol} 盘口深度...'):
        df = fetch_real_kline_data(real_symbol, timeframe='1h', limit=100)
    
    if isinstance(df, pd.DataFrame) and not df.empty:
        cur_p = df['close'].iloc[-1]
        res = df['high'].rolling(window=20).max().iloc[-1]
        sup = df['low'].rolling(window=20).min().iloc[-1]
        
        # 1. K 线图改为纯白底色 (plotly_white)
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#2ebd85', increasing_fillcolor='#2ebd85', 
            decreasing_line_color='#f23645', decreasing_fillcolor='#f23645'  
        )])
        fig.add_hline(y=res, line_dash="dot", line_color="#f23645", annotation_text=f"压力位: {res:.2f}", annotation_font_color="#f23645")
        fig.add_hline(y=sup, line_dash="dot", line_color="#2ebd85", annotation_text=f"支撑位: {sup:.2f}", annotation_font_color="#2ebd85")
        
        fig.update_layout(
            template="plotly_white",  # 关键：改为纯白主题
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=20, b=0), height=450
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
        
        col1, col2, col3 = st.columns(3)
        col1.metric("现价 (USDT)", f"{cur_p:.4f}")
        col2.metric("上方强压", f"{res:.4f}", delta_color="inverse")
        col3.metric("下方铁底", f"{sup:.4f}")
        
        st.markdown("### AI 动态决策")
        
        range_total = res - sup
        distance_to_sup = cur_p - sup
        distance_to_res = res - cur_p
        
        if distance_to_sup < range_total * 0.2:
            ai_signal = "建议做多 (LONG)"
            ai_color = "#2ebd85"
            ai_desc = f"价格靠近底层支撑 {sup:.4f}，空头动能减弱，盈亏比极佳。建议现价建仓多单。"
        elif distance_to_res < range_total * 0.2:
            ai_signal = "建议做空 (SHORT)"
            ai_color = "#f23645"
            ai_desc = f"价格触及上方压制区 {res:.4f}，存在回落风险。建议逢高开空。"
        else:
            ai_signal = "震荡观望 (NEUTRAL)"
            ai_color = "#64748B"
            ai_desc = f"价格处于中轨，方向不明。请等待触碰强压 {res:.4f} 或支撑 {sup:.4f} 后再操作。"

        st.markdown(f"""
        <div class="ai-card">
            <h4 style="color: {ai_color}; margin-top: 0px;">执行指令：{ai_signal}</h4>
            <p style="font-size: 15px; color: #475569; line-height: 1.6;"><strong>逻辑推演：</strong>{ai_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.error("网络加载异常，请刷新重试。")

else:
    st.markdown("<div style='text-align: center; margin-top: 60px;'><h1 class='clean-title'>QUANT ALPHA 机构终端</h1><p style='color: #64748B; font-size: 18px;'>数据驱动 · 极简交易</p></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.warning("请在左侧侧边栏输入授权 UID 解锁行情面板。")
    
    st.markdown("### 终端准入规则")
    st.markdown("""
    1. **绑定邀请码**：通过节点专属链接注册 Deepcoin 账号。
    2. **输入 UID**：在左侧输入 Deepcoin UID 进行身份核验。
    3. **资金要求**：账户需保持活跃以维持授权状态。
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("""
        <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: block; text-align: center; background-color: #2ebd85; color: white; padding: 14px; border-radius: 6px; text-decoration: none; font-size: 16px; font-weight: bold;">
            第一步：点击获取 Deepcoin 授权账户
        </a>
        """, unsafe_allow_html=True)
