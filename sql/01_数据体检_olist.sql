-- P1-1 数据体检 SQL（真实 Olist 版，DBeaver 连 data_olist/olist.db 直接跑，只读）
-- 库: olist.db（SQLite，由 build_olist_db.py 从 8 张官方 csv 导入）

-- 1. 订单状态分布（成交口径决策）
SELECT order_status, COUNT(*) n FROM olist_orders GROUP BY order_status ORDER BY n DESC;

-- 2. 订单时间范围与尾部稀疏（R 参考日决策）
SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM olist_orders;
SELECT substr(order_purchase_timestamp,1,7) ym, COUNT(*) n
FROM olist_orders GROUP BY ym ORDER BY ym;


-- 3. delivered 口径核心数字（RFM 基数）
WITH d AS (SELECT customer_id, order_id FROM olist_orders WHERE order_status='delivered')
SELECT COUNT(DISTINCT c.customer_unique_id) uniq_cust,
       ROUND(SUM(p.payment_value),2) amt_total,
       COUNT(DISTINCT d.order_id) orders_n
FROM d
JOIN olist_customers c ON d.customer_id = c.customer_id
JOIN olist_payments p ON d.order_id = p.order_id;

-- 4. ★真实结构: 每客户订单数分布（97% 单次购买）
WITH d AS (SELECT o.customer_id, o.order_id FROM olist_orders o WHERE o.order_status='delivered'),
per AS (SELECT c.customer_unique_id u, COUNT(*) cnt
        FROM d JOIN olist_customers c ON d.customer_id=c.customer_id
        GROUP BY c.customer_unique_id)
SELECT MIN(cnt) min_o, MAX(cnt) max_o, ROUND(AVG(cnt),2) avg_o,
       SUM(cnt=1) single_buyers, COUNT(*) total_cust,
       ROUND(100.0*SUM(cnt=1)/COUNT(*),1) single_pct FROM per;

-- 5. 订单金额分布（M 打分用分位数依据）
SELECT COUNT(*) n, MIN(v) min_v, MAX(v) max_v, ROUND(AVG(v),2) avg_v FROM (
  SELECT d.order_id, SUM(p.payment_value) v
  FROM (SELECT order_id FROM olist_orders WHERE order_status='delivered') d
  JOIN olist_payments p ON d.order_id = p.order_id GROUP BY d.order_id);

-- 6. 州分布（画像素材，真实地理）
SELECT customer_state, COUNT(DISTINCT customer_unique_id) u
FROM olist_customers GROUP BY customer_state ORDER BY u DESC LIMIT 10;

-- 7. 支付缺失检查（delivered 无支付记录订单）
SELECT COUNT(*) delivered_total,
       SUM(CASE WHEN p.order_id IS NULL THEN 1 ELSE 0 END) no_payment
FROM (SELECT order_id FROM olist_orders WHERE order_status='delivered') d
LEFT JOIN (SELECT DISTINCT order_id FROM olist_payments) p ON d.order_id = p.order_id;
