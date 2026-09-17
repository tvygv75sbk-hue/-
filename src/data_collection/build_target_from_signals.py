# -*- coding: utf-8 -*-
"""
基于免费可得信号（天气、Wiki页面访问、Trends、节假日）合成游客量目标作为教学用代理变量。
注意：若后续拿到真实门禁数据，请替换此文件的合成逻辑。
"""
import os
import pandas as pd
import numpy as np
import holidays
from datetime import date
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
RAW = os.path.join(ROOT, CONFIG['paths']['data_raw'])
PROCESSED = os.path.join(ROOT, CONFIG['paths']['data_processed'])
os.makedirs(PROCESSED, exist_ok=True)

start = pd.to_datetime(str(CONFIG['project']['start_date']))
end = pd.to_datetime(str(CONFIG['project']['end_date']))

CN_HOL = holidays.country_holidays('CN', years=list(range(start.year, end.year+1)))


def load_csv(name):
    p = os.path.join(RAW, name)
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def main():
    # 日期基表
    dt = pd.DataFrame({'dt': pd.date_range(start, end, freq='D')})
    dt['year'] = dt['dt'].dt.year
    dt['month'] = dt['dt'].dt.month
    dt['day_of_week'] = dt['dt'].dt.dayofweek
    dt['is_weekend'] = (dt['day_of_week']>=5).astype(int)
    dt['is_holiday'] = dt['dt'].dt.date.map(lambda d: 1 if d in CN_HOL else 0)

    # 天气
    w = load_csv('weather_open_meteo.csv')
    if not w.empty:
        w['dt'] = pd.to_datetime(w['dt'])
    # Wiki
    wiki = load_csv('wikimedia_pageviews.csv')
    if not wiki.empty:
        wiki['dt'] = pd.to_datetime(wiki['dt'])
    # Trends
    tr = load_csv('trends_interest.csv')
    if not tr.empty:
        tr['dt'] = pd.to_datetime(tr['dt'])

    df = dt.merge(w, on='dt', how='left')\
           .merge(wiki, on='dt', how='left')\
           .merge(tr, on='dt', how='left')

    # 缺失填充
    for col in ['temp_mean','temp_max','temp_min','precipitation','wiki_pageviews','trends_interest']:
        if col in df.columns:
            df[col] = df[col].interpolate(limit_direction='both')

    # 合成目标：基准+周末/节假日/天气/热度的线性组合 + 噪声
    base = 4200
    weekend_boost = 0.25
    holiday_boost = 0.8

    # 天气评分（18-24℃最舒适，降雨抑制）
    temp = df['temp_mean'].clip(0, 35)
    comfort = 1 - (abs(temp - 21)/21)  # 0~1
    rain_penalty = (df['precipitation'].fillna(0)/20).clip(0, 1)  # 0~1
    weather_score = (0.7*comfort + 0.3*(1 - rain_penalty))

    # 热度：标准化 wiki 和 trends
    def zscore(s):
        s = s.fillna(s.median())
        return (s - s.mean())/ (s.std()+1e-6)

    hot = 0.6*zscore(df['wiki_pageviews']) + 0.4*zscore(df['trends_interest'])
    hot = (hot - hot.min())/(hot.max()-hot.min()+1e-6)  # 0~1

    visitor = base * (
        1
        + weekend_boost*df['is_weekend']
        + holiday_boost*df['is_holiday']
        + 0.3*weather_score
        + 0.25*hot
    )

    # 噪声
    rng = np.random.default_rng(2025)
    noise = rng.normal(0, 200, size=len(df))
    df['visitor_count'] = (visitor + noise).clip(500, None).round().astype(int)

    # 保存
    out = df[['dt','visitor_count']]
    out.to_csv(os.path.join(PROCESSED, 'visitors_target.csv'), index=False, encoding='utf-8-sig')
    df.to_csv(os.path.join(PROCESSED, 'merged_signals.csv'), index=False, encoding='utf-8-sig')

if __name__ == '__main__':
    main()
