# P1 Olist 真实数据 · 体检事实（build_olist_db.py 生成）

## 0. 导入概览
- olist_customers_dataset.csv: 99441 行 / 5 列 / 编码 utf-8-sig
- olist_orders_dataset.csv: 99441 行 / 8 列 / 编码 utf-8-sig
- olist_order_payments_dataset.csv: 103886 行 / 5 列 / 编码 utf-8-sig
- olist_order_items_dataset.csv: 112650 行 / 7 列 / 编码 utf-8-sig
- olist_products_dataset.csv: 32951 行 / 9 列 / 编码 utf-8-sig
- olist_sellers_dataset.csv: 3095 行 / 4 列 / 编码 utf-8-sig
- olist_order_reviews_dataset.csv: 99224 行 / 7 列 / 编码 utf-8-sig
- product_category_name_translation.csv: 71 行 / 2 列 / 编码 utf-8-sig

**orders 状态分布**
```
  delivered	96478
  shipped	1107
  canceled	625
  unavailable	609
  invoiced	314
  processing	301
  created	5
  approved	2
```

**orders 日期范围(购买时间)**
```
  2016-09-04 21:15:19	2018-10-17 17:30:18
```

**orders 唯一性**
```
  99441	99441
```

**delivered 口径订单数与客户数**
```
  96478	96478
```

**customers unique 客户数 vs 订单客户数**
```
  99441	96096
```

**payments 行数与异常**
```
  103886	99440	0	0
```

**items 行数/覆盖订单/孤儿**
```
  112650	98666
```

**delivered 且 orders 有 payment 记录数(join)**
```
  96477
```

**每 unique 客户 delivered 订单数分布(前几档)**
```
  8d50f5eadf50201ccdcedfb9e2ac8455	15
  3e43e6105506432c953e165fb2acf44c	9
  ca77025e7201e3b30c44b472ff346268	7
  6469f99c1f9dfae7733b25662e7f1782	7
  1b6c7548a2a1f9037c1fd3ddfed95f33	7
  f0e310a6839dce9de1638e0fe5ab282a	6
  dc813062e0fc23409cd255f7f53c7074	6
  63cfc61cee11cbe306bff5857d00bfe4	6
  47c1a3033b8b77b3ab6e109eb4d5fdf3	6
  12f5d6e1cbf93dafd9dcc19095df0b3d	6
```

**customers 州分布 Top10**
```
  SP	40302
  RJ	12384
  MG	11259
  RS	5277
  PR	4882
  SC	3534
  BA	3277
  DF	2075
  ES	1964
  GO	1952
```

**reviews 评分分布**
```
  1	11424
  2	3151
  3	8179
  4	19142
  5	57328
```

**reviews 缺失**
```
  99224	0
```

**order 时间是否有跨年月**
```
  2016-09	4
  2016-10	324
  2016-12	1
  2017-01	800
  2017-02	1780
  2017-03	2682
  2017-04	2404
  2017-05	3700
  2017-06	3245
  2017-07	4026
  2017-08	4331
  2017-09	4285
  2017-10	4631
  2017-11	7544
  2017-12	5673
  2018-01	7269
  2018-02	6728
  2018-03	7211
  2018-04	6939
  2018-05	6873
  2018-06	6167
  2018-07	6292
  2018-08	6512
  2018-09	16
  2018-10	4
```
