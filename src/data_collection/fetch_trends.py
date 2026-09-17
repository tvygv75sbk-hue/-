# -*- coding: utf-8 -*-
import os, json
import pandas as pd
from datetime import datetime
from pytrends.request import TrendReq
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
RAW_DIR = os.path.join(ROOT, CONFIG['paths']['data_raw'])
os.makedirs(RAW_DIR, exist_ok=True)

kw = CONFIG['project']['trends_keyword']
start = str(CONFIG['project']['start_date'])
end = str(CONFIG['project']['end_date'])


def _fallback_zero():
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    dates = pd.date_range(start_dt, end_dt, freq='D')
    df = pd.DataFrame({'dt': dates.date, 'trends_interest': 0})
    df.to_csv(os.path.join(RAW_DIR, 'trends_interest.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(RAW_DIR, 'trends.meta.json'), 'w', encoding='utf-8') as f:
        json.dump({'fallback': True, 'reason': 'trends_connect_timeout_or_blocked', 'rows': len(df)}, f, ensure_ascii=False, indent=2)


def main():
    try:
        # 加超时与最小化依赖；若网络不可达，则走异常分支
        pytrends = TrendReq(hl='zh-CN', tz=480, timeout=(2, 8))
        timeframe = f'{start} {end}'
        pytrends.build_payload([kw], timeframe=timeframe, geo='CN')
        df = pytrends.interest_over_time()
        if df.empty or kw not in df.columns:
            _fallback_zero()
            return
        df = df.reset_index().rename(columns={'date':'dt', kw:'trends_interest'})
        df['dt'] = pd.to_datetime(df['dt']).dt.date
        # 若非日频，重采样到日频（前向填充）
        df = df.set_index('dt').asfreq('D').ffill().reset_index()
        df.to_csv(os.path.join(RAW_DIR, 'trends_interest.csv'), index=False, encoding='utf-8-sig')
        with open(os.path.join(RAW_DIR, 'trends.meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'fallback': False, 'rows': len(df)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('WARN: Google Trends 获取失败，使用零值占位继续。', str(e))
        _fallback_zero()

if __name__ == '__main__':
    main()
