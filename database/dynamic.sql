USE dali_tourism_forecast;

-- 在 fact_visitors 上添加更新时间字段并创建触发器
ALTER TABLE fact_visitors ADD COLUMN updated_at DATETIME NULL;
DELIMITER $$
CREATE TRIGGER trg_visitors_updated
BEFORE UPDATE ON fact_visitors
FOR EACH ROW
BEGIN
  SET NEW.updated_at = NOW();
END$$
DELIMITER ;

-- 存储过程：计算7日移动平均到一张汇总表
CREATE TABLE IF NOT EXISTS agg_visitors_7d (
  dt DATE PRIMARY KEY,
  visitor_ma7 DOUBLE
);
DELIMITER $$
CREATE PROCEDURE sp_refresh_visitors_ma7()
BEGIN
  REPLACE INTO agg_visitors_7d (dt, visitor_ma7)
  SELECT d.dt,
         AVG(v2.visitor_count) AS visitor_ma7
  FROM dim_date d
  LEFT JOIN fact_visitors v2 ON v2.dt BETWEEN DATE_SUB(d.dt, INTERVAL 6 DAY) AND d.dt
  GROUP BY d.dt;
END$$
DELIMITER ;
