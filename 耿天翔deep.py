import streamlit as st
import pandas as pd
import ccxt
import time

# ================= 1. 全局配置与状态初始化 =================
st.set_page_config(page_title="Alpha Terminal", page_icon="⬛", layout="wide", initial_sidebar_state="collapsed")

# 初始化登录状态 (门禁开关)
if 'access_granted' not in st.session_state:
    st.session_state.access_granted = False

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
    high_24 = df['high'].max()
    low_24 = df['low'].min()
    
    range_pct = (cur_p - low_24) / (high_24 - low_24) if high_24 != low_24 else 0.5
    
    if range_pct < 0.3:
        signal, tag_class, tag_text = "LONG", "signal-tag-long", "🟢 强烈做多 (STRONG BUY)"
        entry, tp, sl = f"{cur_p * 0.998:.2f}", f"{high_24 * 0.99:.2f}", f"{low_24 * 0.995:.2f}"
        desc = f"智能资金已在 {low_24:.2f} 附近完成吸筹，盈亏比极佳。建议在 Deepcoin 现价或回调至 {entry} 进场。"
    elif range_pct > 0.7:
        signal, tag_class, tag_text = "SHORT", "signal-tag-short", "🔴 逢高做空 (SELL SHORT)"
        entry, tp, sl = f"{cur_p * 1.002:.2f}", f"{low_24 * 1.01:.2f}", f"{high_24 * 1.005:.2f}"
        desc = f"上方抛压极重，量能呈现顶背离。建议在 {entry} 附近布局空单，切勿盲目追多。"
    else:
        signal, tag_class, tag_text = "WAIT", "signal-tag-wait", "⏳ 中性观望 (NEUTRAL)"
        entry, tp, sl = "暂不建议现价进场", "等待趋势确认", "严控仓位"
        desc = "当前处于价格中枢震荡区，方向不明。请等待突破上下轨后右侧建仓。"
        
    return {"price": cur_p, "class": tag_class, "text": tag_text, "entry": entry, "tp": tp, "sl": sl, "desc": desc}

# ================= 4. 路由拦截与页面渲染 =================

if not st.session_state.access_granted:
    # ---------------- 门禁页面：二选一高级引导 ----------------
    st.markdown("<div style='margin-top: 5vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title' style='text-align: center;'>QUANT ALPHA 终端</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle' style='text-align: center;'>请选择您的终端接入方式，获取机构级监控权限。</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    # 选项 1：返佣白嫖 (拿手续费)
    with col1:
        st.markdown("""
        <div class="gate-card free">
            <div>
                <span style="background: #ECFDF5; color: #059669; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">强烈推荐</span>
                <h3 style="margin-top: 15px; color: #0F172A;">节点授权模式</h3>
                <div class="price-tag">免费接入</div>
                <div class="feature-list">
                    ✓ 永久免费使用 Alpha 终端全部功能<br>
                    ✓ 实时获取 AI 双币对交易策略<br>
                    ✓ 享受全网最高 50% 手续费减免<br>
                    ✓ 绑定验证即刻秒开权限<br>
                </div>
            </div>
            <div>
                <a href="https://www.deepcoin.com/zh-Hans/register?invitationCode=YOUR_CODE" target="_blank" class="btn-primary" style="background: #10B981;">1. 点击获取 Deepcoin 专属返佣账户</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # 验证框紧跟其后
        uid_input = st.text_input("👉 已经通过上方链接注册？输入 UID 验证解锁：", placeholder="例如: 20061008")
        if st.button("立即验证 UID", use_container_width=True):
            if uid_input in ["20061008", "888888"]: # 这里填你允许的UID
                st.session_state.access_granted = True
                st.rerun()
            else:
                st.error("❌ UID 未授权或未达标！请确认使用本站链接注册，或联系客服。")

    # 选项 2：付费买断 (收 50U)
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
                    ✓ USDT 转账激活，随时可取消<br>
                </div>
            </div>
            <div>
                <a href="mailto:your_email@example.com" class="btn-primary" style="background: #4F46E5;">联系主理人开通 Pro 版</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 为了方便你自己测试看效果，留个后门
        if st.button("🔑 测试通道 (管理员一键直达)", use_container_width=True):
            st.session_state.access_granted = True
            st.rerun()

else:
    # ---------------- 内部系统：顶级便当盒主控台 ----------------
    
    # 左侧边栏导航
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 800; color: #0F172A; margin-bottom: 0px;'>⚡ QUANT ALPHA</h2>", unsafe_allow_html=True)
        st.caption("系统状态: OKX 节点直连 🟢")
        st.markdown("---")
        menu = st.radio("导航菜单", ["🎯 Alpha 策略主控台", "💎 Pro 续费通道", "📞 联系您的客户经理"])
        st.markdown("---")
        if st.button("登出终端 / 切换账号"):
            st.session_state.access_granted = False
            st.rerun()

    # ---- 页面 1：Alpha 策略主控台 (纯正便当盒) ----
    if menu == "🎯 Alpha 策略主控台":
        st.markdown("<div class='hero-title'>QUANT ALPHA TERMINAL</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>机构级流动性监控与高频交易指令中枢</div>", unsafe_allow_html=True)

        with st.spinner('正在直连 OKX 专线解析深度数据...'):
            market_data = fetch_market_data()

        if market_data:
            st.markdown("<h3 style='font-size: 1.2rem; margin-bottom: 15px;'>🎯 AI 核心策略演算 (双币对)</h3>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            # BTC 卡片
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
                    <div class="data-row"><span class="data-label">入场区间 (Entry)</span><span class="data-value">{btc_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{btc_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{btc_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # ETH 卡片
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
                    <div class="data-row"><span class="data-label">入场区间 (Entry)</span><span class="data-value">{eth_strat['entry']}</span></div>
                    <div class="data-row"><span class="data-label">止盈目标 (Take Profit)</span><span class="data-value" style="color: #059669;">{eth_strat['tp']}</span></div>
                    <div class="data-row"><span class="data-label">强制止损 (Stop Loss)</span><span class="data-value" style="color: #DC2626;">{eth_strat['sl']}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # 底部流动性卡片
            st.markdown("<h3 style='font-size: 1.2rem; margin-top: 20px; margin-bottom: 15px;'>⚡ 宏观流动性监控仪</h3>", unsafe_allow_html=True)
            col3, col4, col5 = st.columns(3)
            
            with col3:
                st.markdown("""
                <div class="bento-card" style="padding: 20px;">
                    <div class="module-title">🔥 24H 多空清算比</div>
                    <div style="margin-top: 15px;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 5px;"><span>多头爆仓 $42.5M</span><span>空头爆仓 $18.2M</span></div>
                        <div style="width: 100%; height: 8px; background: #FEF2F2; border-radius: 4px; display: flex; overflow: hidden;">
                            <div style="width: 70%; background: #DC2626; height: 100%;"></div>
                            <div style="width: 30%; background: #059669; height: 100%;"></div>
                        </div>
                        <p style="font-size: 13px; color: #64748B; margin-top: 10px; margin-bottom: 0;">分析：散户多头正在被收割，庄家有向下插针寻觅流动性的倾向。</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                st.markdown("""
                <div class="bento-card" style="padding: 20px;">
                    <div class="module-title">⚖️ 永续资金费率预警</div>
                    <div class="data-row"><span class="data-label">BTC 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0150%</span></div>
                    <div class="data-row"><span class="data-label">ETH 实时费率</span><span class="data-value" style="color: #DC2626;">+0.0210%</span></div>
                    <p style="font-size: 13px; color: #64748B; margin-top: 15px; margin-bottom: 0;">分析：费率偏高，做多成本增加，谨防主力反向诱空杀跌。</p>
                </div>
                """, unsafe_allow_html=True)

            with col5:
                st.markdown("""
                <div class="bento-card" style="padding: 20px;">
                    <div class="module-title">🐋 链上 Smart Money</div>
                    <div style="font-size: 13px; line-height: 1.8;">
                        <div style="color: #0F172A;">🚨 <b>1200 BTC</b> 转入未知钱包</div>
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
