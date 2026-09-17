# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
RAW = os.path.join(ROOT, CONFIG['paths']['data_raw'])
PROC = os.path.join(ROOT, CONFIG['paths']['data_processed'])
os.makedirs(PROC, exist_ok=True)


def read_csv_safe(path):
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


def main():
    weather = read_csv_safe(os.path.join(RAW, 'weather_open_meteo.csv'))
    wiki = read_csv_safe(os.path.join(RAW, 'wikimedia_pageviews.csv'))
    trends = read_csv_safe(os.path.join(RAW, 'trends_interest.csv'))
    target = read_csv_safe(os.path.join(PROC, 'visitors_target.csv'))

    for df, col in [(weather,'dt'), (wiki,'dt'), (trends,'dt'), (target,'dt')]:
        if not df.empty:
            df[col] = pd.to_datetime(df[col])

    df = weather.copy()
    for other in [wiki, trends, target]:
        if not other.empty:
            df = df.merge(other, on='dt', how='left')

    # 按日期去重（保留首次出现）
    df = df.drop_duplicates(subset=['dt'])

    # 缺失处理（数值列插值）
    num_cols = df.select_dtypes(include=[np.number]).columns
    for c in num_cols:
        df[c] = df[c].interpolate(limit_direction='both')

    # IQR 异常值检测与截断 + 标记（列存在时才处理）
    def clip_iqr(series: pd.Series):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lb = q1 - 1.5 * iqr
        ub = q3 + 1.5 * iqr
        flag = ((series < lb) | (series > ub)).astype(int)
        clipped = series.clip(lower=lb, upper=ub)
        return clipped, flag

    for col in ['visitor_count', 'wiki_pageviews', 'trends_interest', 'precipitation']:
        if col in df.columns:
            clipped, flag = clip_iqr(df[col])
            df[col] = clipped
            df[f'outlier_flag_{col}'] = flag

    # 基本派生
    df['year'] = df['dt'].dt.year
    df['month'] = df['dt'].dt.month
    df['dayofweek'] = df['dt'].dt.dayofweek
    df['is_weekend'] = (df['dayofweek']>=5).astype(int)

    df = df.sort_values('dt')
    df.to_csv(os.path.join(PROC, 'clean_data.csv'), index=False, encoding='utf-8-sig')
    # 另存为Excel以满足“Excel格式”要求
    try:
        df.to_excel(os.path.join(PROC, 'clean_data.xlsx'), index=False)
    except Exception:
        pass

if __name__ == '__main__':
    main()
