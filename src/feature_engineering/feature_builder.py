# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
PROC = os.path.join(ROOT, CONFIG['paths']['data_processed'])
FINAL = os.path.join(ROOT, CONFIG['paths']['data_final'])
os.makedirs(FINAL, exist_ok=True)


def add_lags(df, col, lags=(1,7,14,30)):
    for L in lags:
        df[f'{col}_lag{L}'] = df[col].shift(L)
    return df

def add_rollings(df, col, windows=(7,14,30)):
    for w in windows:
        df[f'{col}_ma{w}'] = df[col].rolling(w).mean()
        df[f'{col}_std{w}'] = df[col].rolling(w).std()
    return df


def main():
    df = pd.read_csv(os.path.join(PROC, 'clean_data.csv'), parse_dates=['dt'])
    df = df.sort_values('dt').reset_index(drop=True)

    # 目标
    ycol = 'visitor_count'

    # 派生时间特征
    df['weekofyear'] = df['dt'].dt.isocalendar().week.astype(int)
    df['quarter'] = df['dt'].dt.quarter

    # 滞后与滚动（目标）
    df = add_lags(df, ycol, lags=(1,7,14,30))
    df = add_rollings(df, ycol, windows=(7,30))

    # 交通客流量近似代理：基于热度信号的加权与平滑（免费数据替代）
    if 'trends_interest' in df.columns or 'wiki_pageviews' in df.columns:
        if 'trends_interest' in df.columns:
            tr_norm = (df['trends_interest'] - df['trends_interest'].min()) / (df['trends_interest'].max() - df['trends_interest'].min() + 1e-6)
        else:
            tr_norm = 0
        if 'wiki_pageviews' in df.columns:
            wk_norm = (df['wiki_pageviews'] - df['wiki_pageviews'].min()) / (df['wiki_pageviews'].max() - df['wiki_pageviews'].min() + 1e-6)
        else:
            wk_norm = 0
        if isinstance(tr_norm, int):
            df['traffic_proxy'] = wk_norm
        elif isinstance(wk_norm, int):
            df['traffic_proxy'] = tr_norm
        else:
            df['traffic_proxy'] = 0.6 * tr_norm + 0.4 * wk_norm
        # 平滑与滞后
        df['traffic_proxy_ma7'] = df['traffic_proxy'].rolling(7).mean()
        df['traffic_proxy_ma14'] = df['traffic_proxy'].rolling(14).mean()
        df['traffic_proxy_lag7'] = df['traffic_proxy'].shift(7)
        df['traffic_proxy_lag14'] = df['traffic_proxy'].shift(14)

    # 天气滚动
    for c in ['temp_mean','precipitation']:
        if c in df.columns:
            df = add_rollings(df, c, windows=(7,))

    # 丢弃起始缺失（由滞后与滚动造成）
    df = df.dropna().reset_index(drop=True)

    # 选择特征
    features = [
        'is_weekend','month','weekofyear','dayofweek','quarter',
        'temp_mean','temp_max','temp_min','precipitation',
        'wiki_pageviews','trends_interest',
        'traffic_proxy','traffic_proxy_ma7','traffic_proxy_lag7','traffic_proxy_ma14','traffic_proxy_lag14',
        'visitor_count_lag1','visitor_count_lag7','visitor_count_lag14','visitor_count_lag30',
        'visitor_count_ma7','visitor_count_ma30',
        'temp_mean_ma7','precipitation_ma7'
    ]
    feats = [f for f in features if f in df.columns]

    model_df = df[['dt', ycol] + feats]
    os.makedirs(os.path.dirname(os.path.join(FINAL,'model_ready_data.csv')), exist_ok=True)
    model_df.to_csv(os.path.join(FINAL,'model_ready_data.csv'), index=False, encoding='utf-8-sig')

if __name__ == '__main__':
    main()
