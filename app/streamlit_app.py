# -*- coding: utf-8 -*-
"""P1 RFM 用户分层看板（Streamlit）——数据来源 output/*.csv 与图"""
import os
import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # P1_RFM
OUT = os.path.join(BASE, "output")

st.set_page_config(page_title="Olist RFM 用户分层", layout="wide")

st.title("巴西 Olist 电商 · RFM 用户分层看板")
st.caption("数据：Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0)｜口径：已交付且有支付记录 96,477 单 / 93,357 客户 / 金额 BRL｜参考日 2018-09-01")

c1, c2, c3 = st.columns(3)
c1.metric("有效客户", "93,357")
c2.metric("有效成交订单", "96,477")
c3.metric("总交易额 (BRL)", "15,422,461.77")

with st.expander("方法口径"):
    st.markdown("""
- **成交口径**：`order_status = delivered` 且支付表中有记录，共 96,477 单
- **金额口径**：`olist_payments.payment_value` 按订单汇总
- **客户主体**：`customer_unique_id`（同一人多地址合并）
- **R 参考日**：2018-09-01（数据集尾部截断，锚定主体结束日保证可复现）
- **打分**：R/M 动态五分位 1-5 分，≥4 分为高；**F 高低以复购（≥2 单）为界**（97% 客户仅 1 单，数据驱动阈值）
- **分层**：R/F/M 高/低 → 8 类（M 高为"重要"，M 低为"一般"）
- **指标口径**：人均累计消费 = 交易额 ÷ 客户数；客单价 = 交易额 ÷ 订单数（单次客两者相等，复购客人均累计 > 客单价）
""")

st.subheader("1. 分层汇总")
try:
    summary = pd.read_csv(os.path.join(OUT, "segment_summary.csv"), index_col=0)
    disp = summary[["customers", "cust_pct", "revenue", "rev_pct"]].copy()
    disp.columns = ["客户数", "客户占比%", "交易额(BRL)", "交易额占比%"]
    disp["客户占比%"] = disp["客户占比%"].round(2)
    disp["交易额占比%"] = disp["交易额占比%"].round(2)
    disp["交易额(BRL)"] = disp["交易额(BRL)"].map(lambda v: f"{v:,.2f}")
    st.dataframe(disp, width=900)
except FileNotFoundError:
    st.error("缺少 output/segment_summary.csv —— 请先运行 scripts/rfm_pipeline.py")

st.subheader("2. 关键图")
f1, f2 = st.columns(2)
for col, fn in [(f1, "fig1_segment_size_revenue.png"), (f2, "fig2_revenue_share.png")]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        col.image(p, use_container_width=True)
    else:
        col.error(f"缺 {fn}")

st.subheader("3. 客群画像")
try:
    profile = pd.read_csv(os.path.join(OUT, "segment_profile.csv"))
    st.dataframe(profile, width=1000)
except FileNotFoundError:
    st.error("缺少 output/segment_profile.csv")

st.subheader("4. 核心结论")
st.markdown("""
1. **大额单次客是交易额主体，两类客户动作不同**：合计 37.6% 的客户贡献 68.3% 交易额。其中沉睡大额（重要挽留）2.07 万人、40.1% 交易额，做唤醒召回；近期首购（重要发展）1.44 万人、28.2% 交易额，做 30/60 天复购培育。
2. **复购客群极小但价值密度高**：重要价值 + 重要保持共 2,238 人，贡献 5.25% 交易额，优先做 VIP 留存与裂变。
3. **沉睡小额客户数量多、单客价值低**：一般挽留 33,715 人贡献 15.84% 交易额，适合采用低成本自动化批量触达。
4. **客户数量集中在 SP 州**：八个客群的第一大州都是 SP，占比 34%–62%。是否要分州运营，得先做"履约时延 vs 复购"的二级分析。
""")

st.divider()
st.caption("项目：Olist 用户分层（RFM）｜ 计算源码 scripts/rfm_pipeline.py")
