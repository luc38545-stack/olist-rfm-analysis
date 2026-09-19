# -*- coding: utf-8 -*-
"""用 Playwright 对本地 Streamlit 看板做整页截图（交付实测用）。

前置：先启动看板 `streamlit run app/streamlit_app.py`，再运行本脚本。
浏览器：默认用 Playwright 自带的 Chromium；如本机环境特殊，可设环境变量
        CHROME_PATH 指向自己的 chrome.exe。
"""
import os
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8501"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 项目根目录 P1_RFM
OUT = os.path.join(BASE, "output", "shot_dashboard_full.png")
CHROME = os.environ.get("CHROME_PATH") or None

with sync_playwright() as p:
    launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
    if CHROME:
        launch_kwargs["executable_path"] = CHROME
    b = p.chromium.launch(**launch_kwargs)
    pg = b.new_page(viewport={"width": 1440, "height": 2400}, device_scale_factor=1.5)
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(18000)         # 等 Streamlit websocket 渲染完成（画像+结论）
    # 折叠/检查是否渲染出指标卡(判定页面真的出来了)
    body = pg.inner_text("body")
    assert "Olist" in body and "93,357" in body, "页面关键内容缺失: " + body[:200]
    idx = body.find("核心结论")
    msg = ("新结论文案未渲染: " + body[idx:idx + 500]) if idx >= 0 else "核心结论段未找到"
    assert "唤醒召回" in body and "复购培育" in body, msg
    pg.screenshot(path=OUT, full_page=True)
    b.close()
print("OK ->", OUT)
