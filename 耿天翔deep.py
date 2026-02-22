import streamlit as st
import pandas as pd
import numpy as np
import time

# 1. 页面全局配置
st.set_page_config(page_title="Deepcoin 节点极速雷达", page_icon="🚀", layout="wide")

# 2. 侧边栏及导航
st.sidebar.title("🔥 内部核心武器库")
st.sidebar.markdown("---")

# 只有输入了正确的 UID，才会显示具体的菜单内容
valid_uids = ["20061008"]

st.sidebar.markdown("### 🔒 身份验证")
uid_input = st.sidebar.text_input("🔑 输入 深币 UID 解锁功能：", type="password")

if uid_input in valid_uids:
    st.sidebar.success(f"✅ 鉴权通过 | UID: {uid_input}")
    st.sidebar.markdown("---")
    # 创建左侧导航菜单
    menu = st.sidebar.radio(
        "选择武器模块",
        ["📊 宏观大盘监控 (Dashboard)", "🐕 百倍土狗狙击 (Altcoin)", "🩸 巨鲸爆仓雷达 (Liquidation)", "⚙️ API 全自动跟单 (Auto-Trade)"]
    )

    # ==========================
    # 模块 1：宏观大盘
    # ==========================
    if menu == "📊 宏观大盘监控 (Dashboard)":
        st.title("📊 宏观资金面实时看板")
        st.markdown("数据源: Deepcoin 核心节点 | 延迟: 12ms (东京服务器)")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("多空比 (BTC)", "0.85", "-12% 空头占优", delta_color="inverse")
        col2.metric("全网资金费率", "0.0125%", "做多成本上升")
        col3.metric("恐慌贪婪指数", "78", "极度贪婪")
        col4.metric("24H 爆仓总金额", "$ 4.2 亿", "巨幅波动预警")

        st.markdown("### 📈 资金流入量趋势模拟")
        # 搞点随机数据画个折线图装逼
        chart_data = pd.DataFrame(np.random.randn(20, 3), columns=['BTC 流入', 'ETH 流入', '山寨币流入'])
        st.line_chart(chart_data)

    # ==========================
    # 模块 2：土狗狙击
    # ==========================
    elif menu == "🐕 百倍土狗狙击 (Altcoin)":
        st.title("🐕 5分钟极速拉升雷达")
        st.info("🚨 提示：以下币种在过去 5 分钟内交易量放大超 300%，极速插针风险极高！")

        # 搞个假的数据表格，散户最喜欢看这种
        df = pd.DataFrame({
            "交易对": ["$PEPE2/USDT", "$DOGE/USDT", "$MEME/USDT", "$SHIB/USDT"],
            "5分钟涨幅": ["+ 15.2%", "+ 8.5%", "+ 6.1%", "- 4.2%"],
            "量能放大": ["450%", "320%", "280%", "主力出逃"],
            "操作建议": ["🔴 极速做空", "🟢 顺势开多", "🟢 顺势开多", "观望"]
        })
        st.table(df)
        st.button("🔄 强制刷新链上数据 (消耗 API 额度)")

    # ==========================
    # 模块 3：爆仓雷达
    # ==========================
    elif menu == "🩸 巨鲸爆仓雷达 (Liquidation)":
        st.title("🩸 合约清算实时追踪")
        st.error("⚠️ 警告：检测到大规模连环爆仓，大户正在强平！")

        # 弹窗警告效果
        with st.expander("查看最新爆仓详情 (展开)"):
            st.warning("17:42:15 - 深币 $BTC - 某多头大户被清算 150 万 USDT 🩸")
            st.warning("17:41:03 - 深币 $ETH - 某多头大户被清算 80 万 USDT 🩸")
            st.success("17:39:20 - 深币 $SOL - 某空头大户被清算 40 万 USDT 🟢")

        st.markdown("### 狙击策略：等待多头死绝，现价开多，建议杠杆 50X。")

    # ==========================
    # 模块 4：画大饼（吸引他们付费或加大交易）
    # ==========================
    elif menu == "⚙️ API 全自动跟单 (Auto-Trade)":
        st.title("⚙️ 全托管自动化跟单设置")
        st.write("将您的深币 API Key 输入此处，云端服务器将为您 24 小时自动执行上述狙击策略。")

        st.text_input("Deepcoin API Key:")
        st.text_input("Deepcoin Secret Key:", type="password")
        st.slider("设置最大杠杆倍数", 1, 100, 20)

        if st.button("🚀 启动自动跟单引擎"):
            st.error("❌ 您的会员等级不足。自动跟单功能仅对【月交易量 > 50万 USDT】或【付费 100 U/月】的高级节点会员开放。")

else:
    # 未登录状态的拦截页面
    st.title("🚀 Web3 极速量化监控终端")
    st.markdown("---")
    st.info("⚠️ 访客模式：核心监控数据已上锁。")
    st.warning("👉 请在左侧侧边栏输入您的【深币 UID】以解锁全部内部武器库。")
    st.write("还没有深币账号？ 点击 [注册内部高反通道] 获取免费体验资格。")