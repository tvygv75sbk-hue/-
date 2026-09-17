# -*- coding: utf-8 -*-
"""
将清洗/合并后的数据写入
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import url as sa_url
import yaml
import holidays

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
PROC = os.path.join(ROOT, 'data', 'processed')
FINAL = os.path.join(ROOT, 'data', 'final')

MYSQL_URL = os.environ.get('MYSQL_URL')
if not MYSQL_URL:
    # 回退到配置（如未设置环境变量）。强烈建议使用环境变量传入口令。
    dbf = CONFIG.get('db', {}).get('fallback', {})
    user = dbf.get('user', 'root')
    pwd = dbf.get('password', '123456')
    host = dbf.get('host', 'localhost')
    port = dbf.get('port', 3306)
    dbname = dbf.get('database', 'dali_tourism_forecast')
    MYSQL_URL = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{dbname}?charset=utf8mb4"

def _read_csv(path):
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

def _ensure_db_and_tables():
    # 确保数据库与必需表/视图存在
    url_obj = sa_url.make_url(MYSQL_URL)
    dbname = url_obj.database
    # 先连到服务器级别，创建数据库（如果不存在）
    base_url = url_obj.set(database=None)
    base_engine = create_engine(base_url)
    with base_engine.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {dbname} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    # 再连目标库，创建表/视图（如不存在）
    engine = create_engine(MYSQL_URL, pool_recycle=3600)
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dim_date (
          dt DATE PRIMARY KEY,
          year INT, month INT, day INT,
          week_of_year INT, day_of_week INT,
          is_weekend TINYINT(1),
          is_holiday TINYINT(1),
          holiday_name VARCHAR(64)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fact_weather (
          dt DATE PRIMARY KEY,
          temp_mean DOUBLE, temp_max DOUBLE, temp_min DOUBLE,
          precipitation DOUBLE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fact_interest (
          dt DATE PRIMARY KEY,
          wiki_pageviews INT,
          trends_interest INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fact_visitors (
          dt DATE PRIMARY KEY,
          visitor_count INT,
          source VARCHAR(32)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        # 视图
        conn.execute(text("""
        CREATE OR REPLACE VIEW vw_model_data AS
        SELECT d.dt,
               w.temp_mean, w.temp_max, w.temp_min, w.precipitation,
               i.wiki_pageviews, i.trends_interest,
               d.is_weekend, d.is_holiday, d.week_of_year, d.day_of_week, d.month,
               v.visitor_count
        FROM dim_date d
        LEFT JOIN fact_weather w ON d.dt = w.dt
        LEFT JOIN fact_interest i ON d.dt = i.dt
        LEFT JOIN fact_visitors v ON d.dt = v.dt;
        """))


def main():
    _ensure_db_and_tables()
    clean = _read_csv(os.path.join(PROC, 'clean_data.csv'))
    if clean.empty:
        raise SystemExit('未找到 clean_data.csv，请先运行清洗与构建脚本。')
    clean['dt'] = pd.to_datetime(clean['dt'])

    # 构造 dim_date
    rng = pd.date_range(clean['dt'].min(), clean['dt'].max(), freq='D')
    cn_hol = holidays.country_holidays('CN', years=list(range(rng.min().year, rng.max().year + 1)))
    dim_date = pd.DataFrame({'dt': rng})
    dim_date['year'] = dim_date['dt'].dt.year
    dim_date['month'] = dim_date['dt'].dt.month
    dim_date['day'] = dim_date['dt'].dt.day
    dim_date['week_of_year'] = dim_date['dt'].dt.isocalendar().week.astype(int)
    dim_date['day_of_week'] = dim_date['dt'].dt.dayofweek
    dim_date['is_weekend'] = (dim_date['day_of_week'] >= 5).astype(int)
    dim_date['is_holiday'] = dim_date['dt'].dt.date.map(lambda d: 1 if d in cn_hol else 0)
    dim_date['holiday_name'] = dim_date['dt'].dt.date.map(lambda d: cn_hol.get(d, None))
    dim_date['dt'] = dim_date['dt'].dt.date

    # fact_weather
    wcols = ['dt', 'temp_mean', 'temp_max', 'temp_min', 'precipitation']
    fact_weather = clean[[c for c in wcols if c in clean.columns]].copy()
    fact_weather['dt'] = pd.to_datetime(fact_weather['dt']).dt.date

    # fact_interest
    icols = ['dt', 'wiki_pageviews', 'trends_interest']
    fact_interest = clean[[c for c in icols if c in clean.columns]].copy()
    fact_interest['dt'] = pd.to_datetime(fact_interest['dt']).dt.date

    # fact_visitors（优先使用 visitors_target.csv；否则用 clean_data）
    vt = _read_csv(os.path.join(PROC, 'visitors_target.csv'))
    if not vt.empty:
        vt['dt'] = pd.to_datetime(vt['dt']).dt.date
        fact_visitors = vt.rename(columns={'visitor_count': 'visitor_count'}).copy()
        fact_visitors['source'] = 'signals'
    else:
        vcols = ['dt', 'visitor_count']
        fact_visitors = clean[[c for c in vcols if c in clean.columns]].copy()
        fact_visitors['dt'] = pd.to_datetime(fact_visitors['dt']).dt.date
        fact_visitors['source'] = 'signals'

    sdate = min(dim_date['dt'])
    edate = max(dim_date['dt'])

    engine = create_engine(MYSQL_URL, pool_recycle=3600)
    with engine.begin() as conn:
        # 清区间数据，避免重复
        for tbl in ['dim_date', 'fact_weather', 'fact_interest', 'fact_visitors']:
            conn.execute(text(f"DELETE FROM {tbl} WHERE dt BETWEEN :s AND :e"), {"s": sdate, "e": edate})
        # 追加写入
        dim_date.to_sql('dim_date', conn, if_exists='append', index=False)
        if not fact_weather.empty:
            fact_weather.to_sql('fact_weather', conn, if_exists='append', index=False)
        if not fact_interest.empty:
            fact_interest.to_sql('fact_interest', conn, if_exists='append', index=False)
        if not fact_visitors.empty:
            fact_visitors.to_sql('fact_visitors', conn, if_exists='append', index=False)
        # 尝试刷新7日均值（若已创建存储过程）
        try:
            conn.execute(text('CALL sp_refresh_visitors_ma7()'))
        except Exception:
            pass

    print(f"已写入 MySQL：{sdate} ~ {edate}")

if __name__ == '__main__':
    main()
