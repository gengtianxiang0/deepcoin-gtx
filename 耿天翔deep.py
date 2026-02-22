import streamlit as st
import pandas as pd
import numpy as np
import time

# 1. 页面全局配置 (宽屏，深色模式)
st.set_page_config(page_title="Deepcoin Alpha 终端", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# 2. 隐藏 Streamlit 官方水印 (极其关键：让散户觉得这是你花大价钱自己开发的独立系统)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 3. 侧边栏及高级导航
st.sidebar.markdown("## ⚡ Deepcoin Alpha 节点")
st.sidebar.caption("服务器节点: Tokyo-AWS-01 | 延迟: 8ms 🟢")
st.sidebar.markdown("---")

valid_uids = ["20061008", "888888"]

st.sidebar.markdown("### 🔐 节点鉴权系统")
uid_input = st.sidebar.text_input("🔑 输入 深币 UID 解锁引擎：", type="password")

if uid_input in valid_uids:
    # 模拟高级加载过程
    with st.sidebar.status("正在连接交易所底层专线...", expanded=True) as status:
        st.write("获取深币 API 接口...")
        time.sleep(0.5)
        st.write("校验 UID 节点归属...")
        time.sleep(0.5)
        st.write("加载高频合约策略组...")
        time.sleep(0.5)
        status.update(label="✅ 专线连接成功！", state="complete", expanded=False)
    
    st.sidebar.success(f"尊贵的 Alpha 会员 | UID: {uid_input}")
    st.sidebar.markdown("---")
    
    # 核心主界面：使用多标签页 (Tabs) 让界面更整洁专业
    st.title("⚡ Web3 高频量化狙击终端 (PRO)")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📊 宏观资金看板", "🚀 异动土狗雷达", "🩸 巨鲸清算追踪"])
    
    # --- 标签页 1：大盘数据 ---
    with tab1:
        st.markdown("#### 资金面实时监控")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("全网多空比 (1H)", "0.82", "-5.4% 空头强势", delta_color="inverse")
        col2.metric("大饼市占率", "52.4%", "+1.2%")
        col3.metric("深币全局资金费率", "0.025%", "做多成本极高", delta_color="inverse")
        col4.metric("贪婪恐慌指数", "79", "极度贪婪 🔴")
        
        st.markdown("#### 📈 主力资金净流入 (模拟模型)")
        # 生成更平滑的模拟图表
        chart_data = pd.DataFrame(np.random.randn(50, 2).cumsum(axis=0), columns=['大户买盘', '散户抛压'])
        st.area_chart(chart_data)

    # --- 标签页 2：土狗雷达 ---
    with tab2:
        st.markdown("#### 🐕 山寨币 5 分钟极速暴涨榜")
        st.info("💡 策略提示：监控到以下币种存在异常放量，疑似庄家拉盘，注意插针风险！建议在深币使用低倍杠杆快进快出。")
        
        # 使用更高级的 dataframe 渲染
        df = pd.DataFrame({
            "交易对": ["$PEPE2/USDT", "$WIF/USDT", "$BOME/USDT", "$DOGE/USDT"],
            "5M涨幅": ["+ 18.5%", "+ 12.1%", "+ 8.4%", "- 2.1%"],
            "量能骤增": ["650%", "420%", "310%", "无异动"],
            "链上异动": ["巨鲸建仓 200万U", "内部钱包分发", "合约大户爆仓", "散户博弈"]
        })
        st.dataframe(df, use_container_width=True)
        
        if st.button("⚡ 强制刷新链上数据"):
            with st.spinner('正在通过 API 抓取深币最新盘口...'):
                time.sleep(1)
            st.success('抓取完成！数据已是最新。')

    # --- 标签页 3：爆仓追踪 ---
    with tab3:
        st.markdown("#### 🩸 高倍杠杆清算地图")
        st.error("🚨 检测到空头连环踩踏，流动性枯竭！")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.warning("⏱️ 1分钟前 | $BTC | 空头爆仓 250 万 USDT 🩸")
            st.warning("⏱️ 3分钟前 | $ETH | 空头爆仓 120 万 USDT 🩸")
        with col_b:
            st.success("⏱️ 5分钟前 | $SOL | 多头爆仓 50 万 USDT 🟢")
            st.success("⏱️ 8分钟前 | $ORDI| 多头爆仓 30 万 USDT 🟢")
            
        st.markdown("##### 🤖 机器推荐操作：等待这波清算结束，现价开空，杠杆建议 20X-50X。")

else:
    # 拦截页面优化
    st.title("⚡ Web3 高频量化狙击终端")
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.warning("⚠️ 核心监控引擎已上锁。当前为访客模式。")
        st.write("本终端直连深币 Deepcoin 底层节点，包含极速土狗雷达、高频爆仓追踪等核心武器。")
        st.write("👉 **请在左侧侧边栏输入您的【深币 UID】以免费解锁全部权限。**")
    with col2:
        st.info("💡 还没有深币账号？")
        st.markdown("[🔗 点击获取内部 50% 手续费返佣注册通道](https://你的深币推广链接.com)")
