# -*- coding: utf-8 -*-
"""下载 Olist 公开数据集（8 张 CSV）到 data_olist/。

数据来源: Kaggle "Brazilian E-Commerce Public Dataset by Olist"
许可: CC BY-NC-SA 4.0（非商用、须署名、衍生作品同协议共享）
镜像: github.com/cstuer/olist-ecommerce-analysis (raw/main/raw/*.csv)

用法:
    python scripts/download_data.py            # 只下载缺失文件
    python scripts/download_data.py --force    # 强制全部重下

说明:
    - 跳过 geolocation 表（61MB，本分析未使用）
    - 数据文件较大，建议上传 GitHub 时用本脚本替代直接提交 CSV（见 README）
"""
import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # P1_RFM
DATA_DIR = os.path.join(BASE_DIR, "data_olist")

MIRROR_URL = "https://raw.githubusercontent.com/cstuer/olist-ecommerce-analysis/main/raw"
FILES = [
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]
# 官方获取方式（Kaggle 需账号）: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce


def main():
    force = "--force" in sys.argv
    os.makedirs(DATA_DIR, exist_ok=True)
    ok, fail = 0, 0
    for name in FILES:
        dest = os.path.join(DATA_DIR, name)
        if os.path.exists(dest) and not force:
            print(f"[skip] {name} (已存在，--force 重下)")
            continue
        url = f"{MIRROR_URL}/{name}"
        print(f"[get ] {name} <- {url}")
        try:
            urllib.request.urlretrieve(url, dest)
            size = os.path.getsize(dest) / 1024 / 1024
            print(f"       {size:.1f} MB -> {dest}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {name}: {e}")
            fail += 1
    print(f"\n完成: 新下载 {ok} 个, 失败 {fail} 个")
    if fail:
        sys.exit(1)
    # 提示: 下载后再建库
    print("下一步: python scripts/build_olist_db.py  （由 CSV 重建 data_olist/olist.db）")


if __name__ == "__main__":
    main()
