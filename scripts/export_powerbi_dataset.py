# -*- coding: utf-8 -*-
"""导出 Power BI 建模用数据集。

产出 output/powerbi/ 下三张表：
  pbi_fact_customer.csv  客户级宽表（RFM + 州 + 首末单 + 主支付 + 评分）
  pbi_fact_order.csv     订单级事实表（供时间趋势 / 地图下钻）
  pbi_dim_segment.csv    客群维表（含排序与运营动作，供切片器与标签）

口径与 scripts/rfm_pipeline.py 保持一致：
  delivered 且有支付 96,477 单 / customer_unique_id 非空 93,357 客户 / 15,422,461.77 BRL
"""
import os
import sqlite3

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data_olist", "olist.db")
OUT = os.path.join(BASE, "output", "powerbi")
REF_DATE = "2018-09-01"
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)

orders = pd.read_sql_query(
    "SELECT order_id, customer_id, order_status, order_purchase_timestamp FROM olist_orders",
    con,
)
payments = pd.read_sql_query(
    "SELECT order_id, payment_type, payment_value FROM olist_payments", con
)
payments["payment_value"] = pd.to_numeric(payments["payment_value"])
customers = pd.read_sql_query(
    "SELECT customer_id, customer_unique_id, customer_state, customer_city FROM olist_customers",
    con,
)
reviews = pd.read_sql_query("SELECT order_id, review_score FROM olist_reviews", con)
reviews["review_score"] = pd.to_numeric(reviews["review_score"], errors="coerce")  # 建表为 TEXT
seg = pd.read_csv(os.path.join(BASE, "output", "rfm_segments.csv"))
con.close()

# 订单级支付：一单多支付行需先汇总，否则金额与订单数都会重复放大
pay_sum = payments.groupby("order_id", as_index=False)["payment_value"].sum()
# 主支付方式：按该订单支付金额最大的那一行
pay_type = (
    payments.sort_values("payment_value", ascending=False)
    .drop_duplicates("order_id")[["order_id", "payment_type"]]
)
rev = reviews.groupby("order_id", as_index=False)["review_score"].max()

o = orders[orders["order_status"] == "delivered"].merge(pay_sum, on="order_id", how="inner")
o = o.merge(pay_type, on="order_id", how="left")
o = o.merge(customers, on="customer_id", how="left")
o = o[o["customer_unique_id"].notna()].copy()
o = o.merge(rev, on="order_id", how="left")
o["ts"] = pd.to_datetime(o["order_purchase_timestamp"])
o["order_date"] = o["ts"].dt.date

# ---------- 客户级宽表 ----------
first_state = (
    o.sort_values("ts").drop_duplicates("customer_unique_id")[
        ["customer_unique_id", "customer_state", "customer_city"]
    ]
)
agg = o.groupby("customer_unique_id", as_index=False).agg(
    first_order=("ts", "min"),
    last_order=("ts", "max"),
    orders=("order_id", "count"),
    monetary=("payment_value", "sum"),
    avg_review=("review_score", "mean"),
)
cust = seg.merge(agg, on="customer_unique_id", how="left")
cust = cust.merge(first_state, on="customer_unique_id", how="left")
cust["first_order_date"] = cust["first_order"].dt.date
cust["last_order_date"] = cust["last_order"].dt.date
cust["avg_review"] = cust["avg_review"].round(2)
cust["monetary"] = cust["monetary"].round(2)
cust = cust.rename(
    columns={
        "customer_unique_id": "customer_id",
        "r_days": "recency_days",
        "f": "frequency",
        "m": "monetary_value",
        "customer_state": "state",
        "customer_city": "city",
    }
)
cust = cust[
    [
        "customer_id", "recency_days", "frequency", "monetary_value",
        "r_score", "m_score", "f_score", "segment",
        "state", "city", "orders", "monetary", "avg_review",
        "first_order_date", "last_order_date",
    ]
]

# ---------- 订单级事实表 ----------
seg_map = seg.set_index("customer_unique_id")["segment"]
fo = o.drop(columns=["customer_id"]).copy()  # 订单表内的 customer_id 与 unique_id 同名字段，去掉避免重名
fo["segment"] = fo["customer_unique_id"].map(seg_map)
fo = fo.rename(columns={"customer_unique_id": "customer_id", "customer_state": "state"})
fo["order_year"] = fo["ts"].dt.year
fo["order_month"] = fo["ts"].dt.to_period("M").astype(str)
fo = fo[
    [
        "order_id", "customer_id", "segment", "order_date", "order_year", "order_month",
        "state", "payment_value", "payment_type", "review_score",
    ]
].sort_values("order_date")

# ---------- 客群维表 ----------
dim = pd.DataFrame(
    [
        ("重要价值", "Champions", 1, "复购+高额+近期", "专属客服、提前体验、介绍返券", "保留优先"),
        ("重要保持", "Cant Lose Them", 2, "复购+高额但久未买", "一对一唤回、老客专属券", "保留优先"),
        ("重要发展", "Potential Loyalist", 3, "近期首购高额、未复购", "30/60 天复购培育、品类推荐", "重点培育"),
        ("重要挽留", "At Risk", 4, "沉睡高额单次", "90 天唤醒、大额券、个性化触达", "优先召回"),
        ("一般价值", "Loyal Low Value", 5, "复购+低额", "提客单价、凑单满减", "稳步提升"),
        ("一般保持", "Need Attention", 6, "复购+低额但久未买", "轻量唤回、常规促销触达", "低成本维护"),
        ("一般发展", "New Low Value", 7, "近期首购低额", "首购后培育、小额复购券", "低成本培育"),
        ("一般挽留", "Hibernating", 8, "沉睡低额", "批量邮件低成本触达", "低成本维护"),
    ],
    columns=["segment", "segment_en", "sort", "definition", "action", "priority"],
)

cust.to_csv(os.path.join(OUT, "pbi_fact_customer.csv"), index=False, encoding="utf-8-sig")
fo.to_csv(os.path.join(OUT, "pbi_fact_order.csv"), index=False, encoding="utf-8-sig")
dim.to_csv(os.path.join(OUT, "pbi_dim_segment.csv"), index=False, encoding="utf-8-sig")

# ---------- 口径断言（与 rfm_pipeline.py 对齐）----------
n_cust = cust["customer_id"].nunique()
n_orders = fo["order_id"].nunique()
total_m = cust["monetary_value"].sum()
assert n_cust == 93357, f"客户数应为 93,357，实际 {n_cust}"
assert n_orders == 96477, f"订单数应为 96,477，实际 {n_orders}"
assert abs(total_m - 15422461.77) < 1, f"交易额应为 15,422,461.77，实际 {total_m}"
assert cust["segment"].notna().all(), "客户级宽表存在未匹配客群"

print(f"[OK] 客户级 {n_cust:,} 行 | 订单级 {n_orders:,} 行 | 交易额 {total_m:,.2f} BRL")
print(f"[OK] 输出目录: {OUT}")
for fn in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, fn)
    print(f"     {fn}  ({os.path.getsize(p) / 1024 / 1024:.2f} MB)")
