# -*- coding: utf-8 -*-
"""Olist 真实数据：预览 + 导入 SQLite + 体检事实输出（只读/建库）。
用法: python build_olist_db.py
产出: data_olist/olist.db + P1_RFM/01_数据体检_事实_olist.md
"""
import csv, sqlite3, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 项目根目录 P1_RFM
RAW_DIR = os.path.join(BASE, "data_olist")
DB_PATH = os.path.join(RAW_DIR, "olist.db")
OUT_MD = os.path.join(BASE, "01_数据体检_事实_olist.md")

FILES = {
    "olist_customers_dataset.csv": "olist_customers",
    "olist_orders_dataset.csv": "olist_orders",
    "olist_order_payments_dataset.csv": "olist_payments",
    "olist_order_items_dataset.csv": "olist_items",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "olist_order_reviews_dataset.csv": "olist_reviews",
    "product_category_name_translation.csv": "olist_category_translation",
}

def sniff_encoding(path):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"

def load_csv(path):
    enc = sniff_encoding(path)
    with open(path, "r", encoding=enc, newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        rows = [row for row in rdr]
    return header, rows

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
summ = []
for fn, tbl in FILES.items():
    p = os.path.join(RAW_DIR, fn)
    header, rows = load_csv(p)
    cur.execute(f"DROP TABLE IF EXISTS {tbl}")
    cols = ", ".join(f'"{c}" TEXT' for c in header)
    cur.execute(f'CREATE TABLE {tbl} ({cols})')
    placeholders = ",".join("?" * len(header))
    cur.executemany(f'INSERT INTO {tbl} VALUES ({placeholders})', rows)
    summ.append(f"{fn}: {len(rows)} 行 / {len(header)} 列 / 编码 {sniff_encoding(p)}")
con.commit()

lines = ["# P1 Olist 真实数据 · 体检事实（build_olist_db.py 生成）", ""]
lines.append("## 0. 导入概览")
lines += [f"- {s}" for s in summ]
def table(title, sql):
    lines.append(f"\n**{title}**")
    lines.append("```")
    for r in cur.execute(sql).fetchall():
        lines.append("  " + "\t".join("NULL" if v is None else str(v) for v in r))
    lines.append("```")

table("orders 状态分布", "SELECT order_status, COUNT(*) n FROM olist_orders GROUP BY order_status ORDER BY n DESC")
table("orders 日期范围(购买时间)", "SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM olist_orders")
table("orders 唯一性", "SELECT COUNT(*) total, COUNT(DISTINCT order_id) distinct_id FROM olist_orders")
table("delivered 口径订单数与客户数", "SELECT COUNT(*) orders_n, COUNT(DISTINCT customer_id) cust_n FROM olist_orders WHERE order_status='delivered'")
table("customers unique 客户数 vs 订单客户数", "SELECT COUNT(*) cust_rows, COUNT(DISTINCT customer_unique_id) unique_cust FROM olist_customers")
table("payments 行数与异常", "SELECT COUNT(*) n, COUNT(DISTINCT order_id) orders_n, SUM(payment_value<0) neg, SUM(payment_value IS NULL) null_v FROM olist_payments")
table("items 行数/覆盖订单/孤儿", "SELECT COUNT(*) n, COUNT(DISTINCT order_id) orders_n FROM olist_items")
table("delivered 且 orders 有 payment 记录数(join)", """
SELECT COUNT(DISTINCT o.order_id) orders_n
FROM olist_orders o JOIN olist_payments p ON o.order_id=p.order_id
WHERE o.order_status='delivered'""")
table("每 unique 客户 delivered 订单数分布(前几档)", """
WITH d AS (SELECT o.customer_id FROM olist_orders o WHERE o.order_status='delivered')
SELECT c.customer_unique_id, COUNT(*) cnt
FROM d JOIN olist_customers c ON d.customer_id=c.customer_id
GROUP BY c.customer_unique_id ORDER BY cnt DESC LIMIT 10""")
table("customers 州分布 Top10", "SELECT customer_state, COUNT(DISTINCT customer_unique_id) u FROM olist_customers GROUP BY customer_state ORDER BY u DESC LIMIT 10")
table("reviews 评分分布", "SELECT review_score, COUNT(*) n FROM olist_reviews GROUP BY review_score ORDER BY review_score")
table("reviews 缺失", "SELECT COUNT(*) n, SUM(review_score IS NULL OR review_score='') no_score FROM olist_reviews")
table("order 时间是否有跨年月", "SELECT substr(order_purchase_timestamp,1,7) ym, COUNT(*) n FROM olist_orders GROUP BY ym ORDER BY ym")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
con.close()
print("OK, db:", DB_PATH)
print("---- 摘要 ----")
print("\n".join(summ))
