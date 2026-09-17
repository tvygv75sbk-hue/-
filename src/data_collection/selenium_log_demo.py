# -*- coding: utf-8 -*-
"""
Selenium 日志演示：不爬取平台数据，仅演示“用户行为日志生成”。
运行前需本地可用Chrome及对应chromedriver（或使用Edge+msedgedriver）。
输出: data/raw/selenium_browse_log.csv
"""
import os, time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
os.makedirs(RAW, exist_ok=True)

def main():
    opts = Options()
    opts.add_argument('--headless')
    driver = webdriver.Chrome(options=opts)
    events = []
    try:
        for url in [
            'https://zh.wikipedia.org/wiki/%E5%A4%A7%E7%90%86%E5%8F%A4%E5%9F%8E',
            'https://www.google.com/search?q=%E5%A4%A7%E7%90%86%E5%8F%A4%E5%9F%8E'
        ]:
            t0 = time.time()
            driver.get(url)
            time.sleep(2)
            for _ in range(3):
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
                time.sleep(1)
            load_ms = int((time.time() - t0) * 1000)
            events.append({'ts': datetime.now().isoformat(timespec='seconds'), 'url': url, 'load_ms': load_ms, 'scrolls': 3})
    finally:
        driver.quit()
    pd.DataFrame(events).to_csv(os.path.join(RAW, 'selenium_browse_log.csv'), index=False, encoding='utf-8-sig')

if __name__ == '__main__':
    main()
