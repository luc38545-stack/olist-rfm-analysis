# -*- coding: utf-8 -*-
"""SQL / Python 双实现自动对账测试（P1 复现性校验）— 严格相等版。

对比对象:
    - Python 权威结果: output/segment_summary.csv（由 scripts/rfm_pipeline.py 生成）
    - SQL 复现结果:   sql/04_RFM打分分层_olist.sql 在 data_olist/olist.db 上的执行输出

判定规则（v3 起为严格一致）:
    - 两边合计客户数一致（93,357）
    - 8 个分层的客户数**逐层完全相等**（SQL v3 通过对齐 r_days 截断方式与并列值
      tie-breaking 实现与 pandas rank(method='first') 的完全等价，实测差异 = 0）

用法:
    python scripts/reconcile_sql_python.py
退出码: 0 = PASS, 1 = FAIL
"""
import os
import sqlite3
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # P1_RFM
DB = os.path.join(BASE, "data_olist", "olist.db")
SQL_FILE = os.path.join(BASE, "sql", "04_RFM打分分层_olist.sql")
PY_CSV = os.path.join(BASE, "output", "segment_summary.csv")

ORDER8 = ["重要价值", "重要发展", "重要保持", "重要挽留",
          "一般价值", "一般发展", "一般保持", "一般挽留"]
EXPECT_TOTAL = 93_357


def run_sql():
    with sqlite3.connect(DB) as con:
        sql = open(SQL_FILE, encoding="utf-8").read()
        rows = con.execute(sql).fetchall()
    return {seg: int(n) for seg, n in rows}


def main():
    sql_counts = run_sql()
    py_df = pd.read_csv(PY_CSV)
    py_counts = dict(zip(py_df["segment"], py_df["customers"].astype(int)))

    missing = [s for s in ORDER8 if s not in sql_counts or s not in py_counts]
    if missing:
        print(f"[FAIL] 分层缺失: {missing}")
        sys.exit(1)

    print(f"{'客群':<8}{'pandas':>10}{'SQL':>10}{'差异':>8}")
    all_ok = True
    for s in ORDER8:
        p, q = py_counts[s], sql_counts[s]
        diff = q - p
        ok = diff == 0
        all_ok &= ok
        print(f"{s:<8}{p:>10,}{q:>10,}{diff:>+8,}  {'OK' if ok else 'FAIL'}")

    total_py = sum(py_counts.values())
    total_sql = sum(sql_counts.values())
    print(f"{'合计':<8}{total_py:>10,}{total_sql:>10,}{total_sql - total_py:>+8,}")

    ok = (total_py == EXPECT_TOTAL and total_sql == EXPECT_TOTAL and all_ok)
    print("\nRECONCILE PASSED — SQL 与 pandas 逐层完全一致"
          if ok else "\n!!! RECONCILE FAILED !!!")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
