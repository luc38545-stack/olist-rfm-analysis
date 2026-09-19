-- P1-2 窗口函数验证（olist.db，DBeaver 连 data_olist/olist.db 只读运行）
-- 两个查询在 RFM 分层前验证窗口函数行为，也可作为复用查询模板：
--   查询 1：每客户首末单间隔天数（复购间隔的基础形态）
--   查询 2：每客户金额第 2 高的订单（ROW_NUMBER + 并列值的确定性排序）
-- 客户主体用 customer_unique_id，需 join olist_customers（同一人可能有多个 customer_id）。

-- ---------- 查询 1：每客户首末两单间隔天数（仅 delivered） ----------
WITH ord AS (
  SELECT c.customer_unique_id uid, o.order_purchase_timestamp ts
  FROM olist_orders o JOIN olist_customers c ON o.customer_id = c.customer_id
  WHERE o.order_status = 'delivered'
),
seq AS (
  SELECT uid, ts,
         COUNT(*) OVER (PARTITION BY uid) n
  FROM ord
)
SELECT uid, CAST(ROUND(julianday(MAX(ts)) - julianday(MIN(ts))) AS INT) span_days
FROM seq GROUP BY uid HAVING n >= 2;

-- ---------- 查询 2：每客户金额第 2 高的订单（金额 + 日期） ----------
-- 金额在 olist_payments 按 order_id 汇总；ORDER BY amt DESC, purchase_ts ASC 保证并列时结果确定。
WITH amt AS (
  SELECT order_id, SUM(payment_value) amt FROM olist_payments GROUP BY order_id
),
ord AS (
  SELECT c.customer_unique_id uid, o.order_id, o.order_purchase_timestamp ts, a.amt
  FROM olist_orders o
  JOIN olist_customers c ON o.customer_id = c.customer_id
  JOIN amt a ON o.order_id = a.order_id
  WHERE o.order_status = 'delivered'
),
rk AS (
  SELECT uid, order_id, ts, amt,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY amt DESC, ts ASC) rn
  FROM ord
)
SELECT uid, order_id, amt, ts FROM rk WHERE rn = 2 ORDER BY amt DESC LIMIT 10;
