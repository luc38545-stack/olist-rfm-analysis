-- RFM 打分与 8 类分层（olist.db，DBeaver 只读运行）
-- 口径：delivered + 有支付(96,477) + customer_unique_id 非空 -> 93,357 客户；R 参考日 2018-09-01
-- 规则：R/M 按动态五分位打 1-5 分（rank 比例 floor+1 封顶 5）；F 用实际单数封顶 5
--       高低判定：R/M 分 >= 4 为高；F >= 2（复购）为高 —— 数据驱动（97% 客户仅 1 单）
-- 结果与 scripts/rfm_pipeline.py 逐层一致，可用 scripts/reconcile_sql_python.py 复核
--
-- SQL 与 pandas 对齐时处理的四处差异：
--   ① 支付表一单多行，必须先按 order_id 汇总再 JOIN，否则 COUNT(*) 把订单数算多；
--   ② R 排序要用 DESC（r_days 越小 = 越近 = 分越高），与 pandas rank(ascending=False) 同向；
--   ③ r_days 用 CAST(... AS INT) 截断，ROUND() 四舍五入会比 pandas 的 .dt.days 多算一天；
--   ④ ROW_NUMBER 要补 uid 第二排序键，否则并列值名次不稳定，边界客户会漂移。

WITH payment_by_order AS (          -- ① 支付按订单汇总：一单多支付行只留一行
  SELECT order_id, ROUND(SUM(payment_value), 2) amount
  FROM olist_payments
  GROUP BY order_id
),
base AS (
  SELECT c.customer_unique_id uid,
         CAST(julianday('2018-09-01') - julianday(MAX(o.order_purchase_timestamp)) AS INT) r_days,  -- ③ 截断=floor，同 pandas .dt.days
         COUNT(*) f,                 -- 此时每订单仅一行，COUNT(*) = 订单数
         SUM(po.amount) m
  FROM (SELECT order_id, customer_id, order_purchase_timestamp
        FROM olist_orders WHERE order_status='delivered') o
  JOIN payment_by_order po ON o.order_id = po.order_id
  JOIN olist_customers c ON o.customer_id = c.customer_id
  WHERE c.customer_unique_id IS NOT NULL
  GROUP BY c.customer_unique_id
),
rk AS (
  SELECT uid, r_days, f, m,
         ROW_NUMBER() OVER (ORDER BY r_days DESC, uid) rn_r,  -- ④ 并列按 uid 升序(同 pandas 行序)
         ROW_NUMBER() OVER (ORDER BY m, uid)          rn_m,   -- ④ M 并列同样按 uid
         COUNT(*) OVER () n
  FROM base
),
sc AS (
  SELECT uid, f,
    CASE WHEN CAST(rn_r * 5.0 / n AS INT) + 1 > 5 THEN 5 ELSE CAST(rn_r * 5.0 / n AS INT) + 1 END r_score,
    CASE WHEN CAST(rn_m * 5.0 / n AS INT) + 1 > 5 THEN 5 ELSE CAST(rn_m * 5.0 / n AS INT) + 1 END m_score
  FROM rk
),
seg AS (
  SELECT uid,
    CASE WHEN r_score >= 4 AND f >= 2 AND m_score >= 4 THEN '重要价值'
         WHEN r_score >= 4 AND f <  2 AND m_score >= 4 THEN '重要发展'
         WHEN r_score <  4 AND f >= 2 AND m_score >= 4 THEN '重要保持'
         WHEN r_score <  4 AND f <  2 AND m_score >= 4 THEN '重要挽留'
         WHEN r_score >= 4 AND f >= 2 AND m_score <  4 THEN '一般价值'
         WHEN r_score >= 4 AND f <  2 AND m_score <  4 THEN '一般发展'
         WHEN r_score <  4 AND f >= 2 AND m_score <  4 THEN '一般保持'
         ELSE '一般挽留' END segment
  FROM sc
)
SELECT segment, COUNT(*) customers
FROM seg GROUP BY segment
ORDER BY MIN(CASE segment WHEN '重要价值' THEN 1 WHEN '重要发展' THEN 2 WHEN '重要保持' THEN 3
     WHEN '重要挽留' THEN 4 WHEN '一般价值' THEN 5 WHEN '一般发展' THEN 6
     WHEN '一般保持' THEN 7 ELSE 8 END);
