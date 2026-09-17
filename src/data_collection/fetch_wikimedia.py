# -*- coding: utf-8 -*-
import os, urllib.parse, json, time
from datetime import datetime
import requests
import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
RAW_DIR = os.path.join(ROOT, CONFIG['paths']['data_raw'])
os.makedirs(RAW_DIR, exist_ok=True)

title = CONFIG['project']['wiki_title']
start = str(CONFIG['project']['start_date']).replace('-', '')
end = str(CONFIG['project']['end_date']).replace('-', '')

API = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/zh.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}'


def _fallback_zero():
    # 生成全日期零值，保证后续流程不中断
    start_dt = pd.to_datetime(str(CONFIG['project']['start_date']))
    end_dt = pd.to_datetime(str(CONFIG['project']['end_date']))
    dates = pd.date_range(start_dt, end_dt, freq='D')
    df = pd.DataFrame({'dt': dates, 'wiki_pageviews': 0})
    df.to_csv(os.path.join(RAW_DIR, 'wikimedia_pageviews.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(RAW_DIR, 'wikimedia.meta.json'), 'w', encoding='utf-8') as f:
        json.dump({'fallback': True, 'reason': 'request_failed_or_blocked', 'rows': len(df)}, f, ensure_ascii=False, indent=2)


def main():
    enc_title = urllib.parse.quote(title, safe='')
    url = API.format(title=enc_title, start=start, end=end)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; dali-tourism-edu/1.0)',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip'
    }
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30, headers=headers)
            if r.status_code == 404:
                # 若无页面访问数据，输出空表
                pd.DataFrame(columns=['dt','wiki_pageviews']).to_csv(os.path.join(RAW_DIR, 'wikimedia_pageviews.csv'), index=False)
                return
            r.raise_for_status()
            items = r.json().get('items', [])
            rows = [{'dt': i['timestamp'][:8], 'wiki_pageviews': i['views']} for i in items]
            df = pd.DataFrame(rows)
            df['dt'] = pd.to_datetime(df['dt'])
            df.to_csv(os.path.join(RAW_DIR, 'wikimedia_pageviews.csv'), index=False, encoding='utf-8-sig')
            with open(os.path.join(RAW_DIR, 'wikimedia.meta.json'), 'w', encoding='utf-8') as f:
                json.dump({'url': url, 'rows': len(df), 'fallback': False}, f, ensure_ascii=False, indent=2)
            return
        except Exception as e:
            time.sleep(2 ** attempt)
            if attempt == 2:
                print('WARN: Wikimedia 请求失败，使用零值占位继续。', str(e))
                _fallback_zero()
                return

if __name__ == '__main__':
    main()
