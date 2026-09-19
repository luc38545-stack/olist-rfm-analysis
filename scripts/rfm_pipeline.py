# -*- coding: utf-8 -*-
"""P1 主计算管线：RFM 三维度 -> 打分 -> 8 类分层 -> 画像 -> 图。
数据源: data_olist/olist.db（只读）
产出: output/rfm_base.csv, rfm_segments.csv, segment_summary.csv, segment_profile.csv, 2 张分析图
     + 控制台对账清单
SQL/Pandas 双实现对账由 scripts/reconcile_sql_python.py 独立执行（本文件不做 SQL 对账）。
"""
import os, sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # P1_RFM
DB = os.path.join(BASE, "data_olist", "olist.db")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

REF_DATE = "2018-09-01"   # 口径4: 数据主体截断日
HIGH = 4                  # 打分 1-5, >=4 视为"高"

con = sqlite3.connect(DB)

# ---------- 1) 基础数据 ----------
orders = pd.read_sql_query("SELECT order_id, customer_id, order_purchase_timestamp FROM olist_orders WHERE order_status='delivered'", con)
payments = pd.read_sql_query("SELECT order_id, payment_value FROM olist_payments", con)
payments["payment_value"] = pd.to_numeric(payments["payment_value"])  # 导入建表为 TEXT, 显式转数值
customers = pd.read_sql_query("SELECT customer_id, customer_unique_id, customer_state FROM olist_customers", con)
pay_order = payments.groupby("order_id", as_index=False)["payment_value"].sum()

o = orders.merge(pay_order, on="order_id", how="inner")       # delivered 且有支付 96,477
o = o.merge(customers[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left")
o = o[o["customer_unique_id"].notna()]                        # 防御性过滤: join 后 unique_id 无缺失, 当前数据 0 行被剔除
o["ts"] = pd.to_datetime(o["order_purchase_timestamp"])

# ---------- 2) RFM 三维度 ----------
rfm = o.groupby("customer_unique_id").agg(
    last_ts=("ts", "max"), f=("order_id", "count"), m=("payment_value", "sum"),
).reset_index()
rfm["r_days"] = (pd.Timestamp(REF_DATE) - rfm["last_ts"]).dt.days.astype(int)
rfm = rfm[["customer_unique_id", "r_days", "f", "m"]]
rfm.to_csv(os.path.join(OUT, "rfm_base.csv"), index=False)

n_cust = len(rfm)
print(f"[P1-3] RFM 基础: {n_cust} 客户 | ΣF={rfm['f'].sum()} | ΣM={rfm['m'].sum():,.2f}")
assert n_cust == 93357, "客户数应为 93,357"
assert rfm["f"].sum() == 96477, "ΣF 应为 96,477"
assert abs(rfm["m"].sum() - 15422461.77) < 1, "ΣM 应为 15,422,461.77"

# ---------- 3) 打分 ----------
def pct_score(s, asc=True):
    pct = s.rank(method="first", pct=True) if asc else s.rank(method="first", ascending=False, pct=True)
    sc = (pct * 5).astype(int) + 1   # 排名比例 -> 1..5(全表最高恰为5)
    return sc.clip(upper=5)

rfm["r_score"] = pct_score(rfm["r_days"], asc=False)  # r_days 小(近)=高分
rfm["m_score"] = pct_score(rfm["m"], asc=True)        # m 大=高分
rfm["f_score"] = rfm["f"].clip(upper=5).astype(int)   # F 用实际单数封顶5 (97%客户=1分, 真实信号)
for c in ["r_score", "m_score", "f_score"]:
    assert rfm[c].between(1, 5).all()
# 语义自查: 最近购买(top100 最小 r_days) 的平均 r_score 应接近满分 5
sanity = rfm.nsmallest(100, "r_days")["r_score"].mean()
print(f"[自查] 最近购买 top100 客户平均 r_score = {sanity:.2f} (应≈5)")
assert sanity >= 4.5, "R 得分方向异常"

# 分位边界(供 SQL 复现/审查)
print("\n[P1-4] 分位边界(20/40/60/80):")
for col in ["r_days", "m"]:
    qs = rfm[col].quantile([0.2, 0.4, 0.6, 0.8]).round(2).tolist()
    print(f"  {col}: {qs}")

# ---------- 4) 8 类分层 ----------
# 数据驱动阈值: 97% 客户 F=1, 故 F 高低以"是否复购(F>=2)"为界(而非打分中位数);
# R/M 高低以五分位打分 >=4 为界(前40%为高)。
F_HI = 2
SEG = {
    (1,1,1): "重要价值", (1,1,0): "一般价值", (1,0,1): "重要发展", (1,0,0): "一般发展",
    (0,1,1): "重要保持", (0,1,0): "一般保持", (0,0,1): "重要挽留", (0,0,0): "一般挽留",
}
def seg_of(r):
    return SEG[(int(r["r_score"] >= HIGH), int(r["f"] >= F_HI), int(r["m_score"] >= HIGH))]
rfm["segment"] = rfm.apply(seg_of, axis=1)

ORDER8 = ["重要价值", "重要发展", "重要保持", "重要挽留", "一般价值", "一般发展", "一般保持", "一般挽留"]
rfm.to_csv(os.path.join(OUT, "rfm_segments.csv"), index=False)

summary = rfm.groupby("segment").agg(
    customers=("customer_unique_id", "count"),
    revenue=("m", "sum"),
    f_mean=("f", "mean"),
    m_mean=("m", "mean"),
).reindex(ORDER8).fillna(0)
summary["cust_pct"] = (summary["customers"] / n_cust * 100).round(2)
summary["rev_pct"] = (summary["revenue"] / rfm["m"].sum() * 100).round(2)
summary.to_csv(os.path.join(OUT, "segment_summary.csv"))
print("\n[P1-4] 分层汇总:")
print(summary.to_string())
assert summary["customers"].sum() == n_cust
assert abs(summary["revenue"].sum() - rfm["m"].sum()) < 1

# ---------- 5) SQL/Pandas 双实现对账 ----------
# 由 scripts/reconcile_sql_python.py 独立执行（读 sql/04 输出 vs output/segment_summary.csv，
# 严格逐层相等判定）。本管线不再内嵌 SQL。

# ---------- 6) 画像 ----------
o2 = o.merge(rfm[["customer_unique_id", "segment"]], on="customer_unique_id", how="left")
pay_type = pd.read_sql_query("SELECT order_id, payment_type FROM olist_payments", con)
o3 = o2.merge(pay_type.groupby("order_id", as_index=False).first(), on="order_id", how="left")

profile_rows = []
for seg in ORDER8:
    s = o3[o3["segment"] == seg]
    if len(s) == 0:
        continue
    top_state = s["customer_state"].value_counts().index[0] if len(s) else ""
    top_state_pct = (s["customer_state"] == top_state).mean() * 100
    top_pay = s["payment_type"].value_counts().index[0] if len(s) else ""
    top_pay_pct = (s["payment_type"] == top_pay).mean() * 100
    profile_rows.append({
        "segment": seg, "orders": len(s), "unit_price_mean": round(s["payment_value"].mean(), 2),
        "top_state": top_state, "top_state_pct": round(top_state_pct, 1),
        "top_pay": top_pay, "top_pay_pct": round(top_pay_pct, 1),
        "single_buy_pct": round((s.groupby("customer_unique_id")["order_id"].nunique() == 1).mean() * 100, 1),
    })
profile = pd.DataFrame(profile_rows)
profile.to_csv(os.path.join(OUT, "segment_profile.csv"), index=False)
print("\n[P1-5] 画像:")
print(profile.to_string(index=False))

# ---------- 7) 图(英文标签, 避免中文字体依赖) ----------
fig, ax1 = plt.subplots(figsize=(9, 5))
x = range(len(ORDER8))
ax1.bar(x, summary["customers"] / 1000, color="#85B7EB", label="Customers (k)")
ax2 = ax1.twinx()
ax2.plot(x, summary["revenue"] / 1e6, color="#D85A30", marker="o", label="GMV (M BRL)")
ax1.set_xticks(list(x)); ax1.set_xticklabels([s.replace("客户", "") for s in ORDER8], rotation=30, ha="right")
ax1.set_ylabel("Customers (thousands)"); ax2.set_ylabel("GMV (M BRL)")
ax1.set_title("RFM segments: customer count vs GMV")
fig.legend(loc="upper right"); fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_segment_size_revenue.png"), dpi=130)

seg_rev_share = summary["rev_pct"].sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(7, 5))
ax.barh(seg_rev_share.index[::-1], seg_rev_share.values[::-1], color="#9FE1CB")
ax.set_xlabel("GMV share (%)"); ax.set_title("GMV share by segment")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_revenue_share.png"), dpi=130)

print("\n[图] 已输出 fig1/fig2 -> output/")

# ---------- 8) 对账清单 ----------
checks = {
    "客户总数": (n_cust, 93357),
    "ΣF(订单数)": (int(rfm["f"].sum()), 96477),
    "ΣM(金额)": (round(rfm["m"].sum(), 2), 15422461.77),
    "分层人数合计": (int(summary["customers"].sum()), n_cust),
    "分层金额合计 vs ΣM": (round(summary["revenue"].sum(), 2), round(rfm["m"].sum(), 2)),
}
print("\n[P1-6] 对账清单:")
allok = True
for k, (got, exp) in checks.items():
    ok = abs(got - exp) < (1 if isinstance(exp, float) else 1e-9)
    allok &= ok
    print(f"  {'OK ' if ok else 'FAIL'} {k}: got={got} expected={exp}")
print("\nALL CHECKS PASSED" if allok else "\n!!! CHECK FAILED !!!")
con.close()
