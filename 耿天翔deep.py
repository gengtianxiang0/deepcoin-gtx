import streamlit as st
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime

# ================= 1. 全局配置与极简白 CSS =================
st.set_page_config(page_title="Deepcoin Alpha", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    .stApp { background-color: #FFFFFF; color: #1E293B; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    div[data-testid="stMetric"] { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px 20px; border-radius: 8px; border-left: 4px solid #3B82F6; box-shadow: none; }
    [data-testid="stSidebar"] { background-color: #F1F5F9; border-right: 1px solid #E2E8F0; }
    
    .clean-title { color: #0F172A; font-weight: 800; font-size: 2rem; margin-bottom: 10px; }
    
    /* 核心结论卡片样式 */
    .whale-card { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 5px solid #8B5CF6; padding: 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 15px;}
    .action-card { background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

valid_uids = ["20061008", "888888"]

# ================= 2. 侧边栏：干净的私域漏斗 =================
with st.sidebar:
    st.markdown("<div class='clean-title'>⚡ QUANT ALPHA</div>", unsafe_allow_html=True)
    st.caption("引擎状态: OKX 节点直连 | 🟢 运行中")
    st.markdown("---")
    
    st.markdown("### 🔐 访问授权")
    uid_input = st.text_input("🔑 输入 Deepcoin UID：", type="password", placeholder="例如: 10086...")
    
    st.markdown("---")
    st.markdown("### 👑 VIP 咨询")
    st.info("大资金托管、带单信号接入")
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
        return df
    except Exception as e:
        return str(e)

# ================= 4. 主界面路由 =================
if uid_input in valid_uids:
    st.markdown("<div class='clean-title'>机构级主力监控终端</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 只保留最核心的两大资产
    symbol_map = {"BTC / USDT (比特币)": "BTC/USDT", "ETH / USDT (以太坊)": "ETH/USDT"}
    
    col_sel, col_empty = st.columns([1, 2])
    with col_sel:
        selected_coin = st.selectbox("🎯 选择监控标的", list(symbol_map.keys()))
    
    real_symbol = symbol_map[selected_coin]
    
    with st.spinner(f'正在解析 {real_symbol} 底层数据与主力动向...'):
        df = fetch_real_kline_data(real_symbol, timeframe='1h', limit=100)
    
    if isinstance(df, pd.DataFrame) and not df.empty:
        cur_p = df['close'].iloc[-1]
        res = df['high'].rolling(window=20).max().iloc[-1]
        sup = df['low'].rolling(window=20).min().iloc[-1]
        
        # --- 量能异动测算（判断庄家） ---
        avg_vol = df['volume'].rolling(window=20).mean().iloc[-1]
        cur_vol = df['volume'].iloc[-1]
        vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1
        
        range_total = res - sup
        distance_to_sup = cur_p - sup
        distance_to_res = res - cur_p
        
        # 1. 核心点位卡片
        col1, col2, col3 = st.columns(3)
        col1.metric("⚡ 当前现价 (USDT)", f"{cur_p:.2f}")
        col2.metric("🔴 上方强压 (做空/止盈)", f"{res:.2f}", delta_color="inverse")
        col3.metric("🟢 下方铁底 (做多/止损)", f"{sup:.2f}")
        
        # 2. 庄家动向雷达 (核心洗脑区)
        st.markdown("### 🐋 链上主力与庄家动向")
        
        if vol_ratio > 1.8 and distance_to_sup < range_total * 0.3:
            whale_status = "🚨 检测到巨鲸底部吸筹"
            whale_color = "#10B981" # 绿
            whale_desc = "底层数据显示当前区域出现**异常放量（量能超均值 180%）**。判断为机构或庄家在强支撑位暗中买入建仓，洗盘即将结束，随时可能发起向上插针爆空！"
        elif vol_ratio > 1.8 and distance_to_res < range_total * 0.3:
            whale_status = "⚠️ 主力高位派发预警"
            whale_color = "#EF4444" # 红
            whale_desc = "顶部区域出现**致命放量**，庄家正在利用散户追高的 FOMO 情绪掩护出货。流动性随时枯竭，极易出现断头铡刀式砸盘！"
        elif vol_ratio < 0.8:
            whale_status = "💤 散户博弈阶段 (交投清淡)"
            whale_color = "#64748B" # 灰
            whale_desc = "当前盘口量能萎缩，未监测到大规模机构资金介入。由散户和游资主导盘面，走势跟随大盘联动，极易发生无规律震荡。"
        else:
            whale_status = "🔄 机构量化控盘震荡"
            whale_color = "#F59E0B" # 橙
            whale_desc = "庄家正在利用机器网格算法来回洗盘，反复清理 50X 以上高倍杠杆，为下一波单边行情收集筹码。"

        st.markdown(f"""
        <div class="whale-card">
            <h4 style="color: {whale_color}; margin-top: 0px;">{whale_status}</h4>
            <p style="font-size: 16px; color: #334155; line-height: 1.6; margin-bottom: 0px;">{whale_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 极简操作指令
        st.markdown("### 🤖 极简操作指令")
        
        if distance_to_sup < range_total * 0.2:
            ai_signal = "🟢 现价做多 (LONG)"
            ai_desc = f"进场盈亏比极佳。立刻开多，止盈看向 {res:.2f}，跌破 {sup*0.995:.2f} 坚决止损。"
            bg_color = "#ECFDF5" # 浅绿背景
        elif distance_to_res < range_total * 0.2:
            ai_signal = "🔴 现价做空 (SHORT)"
            ai_desc = f"顶部压制明显，立刻开空，止盈看向中轨区域，突破 {res*1.005:.2f} 坚决止损。"
            bg_color = "#FEF2F2" # 浅红背景
        else:
            ai_signal = "⏳ 挂单等待 (WAIT)"
            ai_desc = f"利润空间不足，严禁现价追单。请在深币挂单：{sup*1.002:.2f} 接多，或 {res*0.998:.2f} 挂空。"
            bg_color = "#F8FAFC" # 浅灰背景

        st.markdown(f"""
        <div class="action-card" style="background-color: {bg_color}; border-left: 4px solid {whale_color};">
            <h4 style="margin-top: 0px;">执行策略：{ai_signal}</h4>
            <p style="font-size: 15px; color: #475569; margin-bottom: 0px;"><strong>行动指南：</strong>{ai_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br><p style='font-size: 13px; color: #94A3B8;'>⚠️ 声明：本推演数据基于 API 实时算力得出，仅限在 Deepcoin 盘口深度下执行。</p>", unsafe_allow_html=True)

    else:
        st.error("网络加载异常，请刷新重试。")

else:
    st.markdown("<div style='text-align: center; margin-top: 60px;'><h1 class='clean-title'>QUANT ALPHA 机构终端</h1><p style='color: #64748B; font-size: 18px;'>去除繁杂图形 · 直击行情底牌</p></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.warning("请在左侧侧边栏输入授权 UID 解锁主力监控面板。")
    
    st.markdown("### 终端准入规则")
    st.markdown("""
    1. **绑定邀请码**：通过节点专属链接注册 Deepcoin 账号。
    2. **输入 UID**：在左侧输入 Deepcoin UID 进行身份核验。
    3. **资金要求**：系统不定期清理零资金与非活跃账户。
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("""
        <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" style="display: block; text-align: center; background-color: #0F172A; color: white; padding: 14px; border-radius: 6px; text-decoration: none; font-size: 16px; font-weight: bold;">
            第一步：点击获取 Deepcoin 授权账户
        </a>
        """, unsafe_allow_html=True)
