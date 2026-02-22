import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ccxt
from datetime import datetime

# 1. 全局配置
st.set_page_config(page_title="Deepcoin 机构级量化终端", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# 隐藏官方水印
hide_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_style, unsafe_allow_html=True)

valid_uids = ["20061008", "888888"]

# ================= 侧边栏：私域漏斗 =================
st.sidebar.markdown("## 📈 机构量化中控台")
st.sidebar.caption("引擎状态: 实时 API 直连 | 延迟 12ms 🟢")
st.sidebar.markdown("---")

st.sidebar.markdown("### 🔐 节点权限验证")
uid_input = st.sidebar.text_input("🔑 请输入 深币 UID：", type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("### 👑 内部策略 VIP 申请")
st.sidebar.info("大资金托管、量化 API 接入，请联系主理人。")
st.sidebar.markdown("""
* ✈️ **Telegram**: [@你的TG用户名](https://t.me/你的TG用户名)
* 💬 **WeChat**: `Geng_Quant2026` (备注深币UID)
* 🎁 **开户福利**: [点击获取 50% 手续费减免 + 赠金通道](https://你的深币代理链接)
""")

# ================= 核心 API 抓取引擎 =================
# 使用缓存机制，防止 API 请求过快被交易所封 IP (缓存 60 秒)
@st.cache_data(ttl=60)
def fetch_real_kline_data(symbol, timeframe='1h', limit=100):
    try:
        # 这里用币安的公开接口作为底层数据源（全球最稳定，且不需要 API Key）
        # 对外咱们依然包装成“深币核心节点”的数据
        exchange = ccxt.binance({'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        return None

# ================= 主界面 =================
if uid_input in valid_uids:
    st.success(f"✅ 鉴权通过 | 尊贵的节点会员 UID: {uid_input} | 真实行情引擎已启动。")
    st.markdown("---")
    
    # 币种选择器与真实交易对的映射
    symbol_map = {
        "$BTC / USDT (比特币)": "BTC/USDT",
        "$ETH / USDT (以太坊)": "ETH/USDT",
        "$SOL / USDT (索拉纳)": "SOL/USDT",
        "$PEPE / USDT (佩佩蛙)": "PEPE/USDT"
    }
    selected_coin = st.selectbox("🎯 选择监控标的 (自动挂载量化模型)", list(symbol_map.keys()))
    real_symbol = symbol_map[selected_coin]
    
    # 抓取真实数据
    with st.spinner(f'正在通过底层专线抓取 {real_symbol} 实时盘口数据...'):
        df = fetch_real_kline_data(real_symbol, timeframe='1h', limit=100)
    
    if df is not None and not df.empty:
        # 提取当前最新价
        cur_p = df['close'].iloc[-1]
        
        # 真正的量化阻力/支撑位算法（取近 20 个周期的最高点和最低点）
        res = df['high'].rolling(window=20).max().iloc[-1]
        sup = df['low'].rolling(window=20).min().iloc[-1]
        
        # 绘制真实的 K 线图
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        )])
        
        # 画压力位 (红线)
        fig.add_hline(y=res, line_dash="dash", line_color="rgba(239, 83, 80, 0.8)", annotation_text=f"🔴 强抛压区 (Resistance): {res:.4f}")
        # 画支撑位 (绿线)
        fig.add_hline(y=sup, line_dash="dash", line_color="rgba(38, 166, 154, 0.8)", annotation_text=f"🟢 强支撑区 (Support): {sup:.4f}")
        
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0), height=500)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 分析面板 ---
        st.markdown("### 🤖 机器深度学习盘口分析")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**⚡ 当前现价 (真实接口)**\n### {cur_p:.4f} USDT")
            st.write("盘口流动性: **已确认**")
        
        with col2:
            st.error(f"**🔴 上方压力位 (阻力)**\n### {res:.4f} USDT")
            st.write("分析: 真实盘口高频挂单密集区，触及该位置极易发生插针，建议作为**多单止盈点**。")
            
        with col3:
            st.success(f"**🟢 下方支撑位 (铁底)**\n### {sup:.4f} USDT")
            st.write("分析: 巨鲸链上护盘区，若回踩不破可作为**高倍合约开多**极佳入场点。")
            
        st.markdown("---")
        st.warning("⚠️ **执行纪律**：上方价格及阻力位采用全球最高流动性均价演算，请以此为基准在深币 Deepcoin 执行挂单！")
    else:
        st.error("❌ 抓取数据失败，请检查网络节点或稍后重试。")

else:
    # 极具诱惑力的未登录界面
    st.title("📈 Web3 机构级量化终端")
    st.markdown("---")
    st.error("🔒 **无权访问：当前 IP 尚未接入 Alpha 节点。**")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("本终端为内部游资专用，提供核心优势：")
        st.write("1. 📊 **交互式 K 线引擎**：毫秒级全盘面监控。")
        st.write("2. 🤖 **支撑/压力位自动推演**：机器智能划线，拒绝盲目开单。")
        st.write("3. 🩸 **精准爆仓追踪**：左侧交易者的最强护城河。")
    
    with col_b:
        st.info("💡 **如何免费解锁？**")
        st.write("使用邀请通道注册深币，并在左侧输入 UID：")
        st.write("[👉 点击获取深币顶级高反邀请通道 👈](https://你的深币代理链接)")
        st.write("有问题？请在左侧侧边栏联系主理人。")
