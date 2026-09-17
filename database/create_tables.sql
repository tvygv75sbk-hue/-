-- MySQL 8 建库与表（大理游客预测）
CREATE DATABASE IF NOT EXISTS dali_tourism_forecast
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dali_tourism_forecast;

-- 日期维度表
CREATE TABLE IF NOT EXISTS dim_date (
  dt DATE PRIMARY KEY,
  year INT, month INT, day INT,
  week_of_year INT, day_of_week INT,
  is_weekend TINYINT(1),
  is_holiday TINYINT(1),
  holiday_name VARCHAR(64)
);

-- 天气表（Open-Meteo）
CREATE TABLE IF NOT EXISTS fact_weather (
  dt DATE PRIMARY KEY,
  temp_mean DOUBLE, temp_max DOUBLE, temp_min DOUBLE,
  precipitation DOUBLE
);

-- 口碑/热度代理表（Wikimedia & Trends）
CREATE TABLE IF NOT EXISTS fact_interest (
  dt DATE PRIMARY KEY,
  wiki_pageviews INT,
  trends_interest INT
);

-- 目标（游客流量或指数）
CREATE TABLE IF NOT EXISTS fact_visitors (
  dt DATE PRIMARY KEY,
  visitor_count INT,
  source VARCHAR(32) -- signals/synthetic/official
);

-- 方便联查的物化视图（可用视图代替）
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
