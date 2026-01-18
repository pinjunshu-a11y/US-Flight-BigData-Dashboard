-- 创建一个宽表视图，方便 Python 和 可视化工具直接调用
-- 解决 Illegal mix of collations 错误：使用 COLLATE 关键字统一排序规则
-- 我们将 JOIN 条件中的字段显式指定为数据库兼容的排序规则
CREATE OR REPLACE VIEW v_flight_performance_analysis AS
SELECT
f.date_key,
c.month,
c.day_of_week,
c.is_weekend,
-- 航司信息：关联你的 dim_airlines 映射表
a.airline_name,
f.airline_code,
-- 机场信息：关联起飞地
o.city_name AS origin_city,
o.state_code AS origin_state,
-- 机场信息：关联目的地
d.city_name AS dest_city,
-- 延误核心数据
f.DepDelayMinutes,
f.DepDel15,
f.Is_Cancelled,
-- 延误分类归因
f.CarrierDelay,
f.WeatherDelay,
f.NASDelay,
f.SecurityDelay,
f.LateAircraftDelay
FROM fact_flights f
LEFT JOIN dim_airlines a
ON f.airline_code = a.airline_code COLLATE utf8mb4_general_ci
LEFT JOIN dim_airports o
ON f.origin_airport = o.airport_code COLLATE utf8mb4_general_ci
LEFT JOIN dim_airports d
ON f.dest_airport = d.airport_code COLLATE utf8mb4_general_ci
LEFT JOIN dim_calendar c
ON f.date_key = c.date_key;

-- 验证视图（查看前10条看名称是否正确映射）
-- 如果运行此行报错，请尝试将上面的 utf8mb4_general_ci 替换为 utf8mb4_0900_ai_ci
SELECT airline_name, origin_city, DepDelayMinutes
FROM v_flight_performance_analysis
LIMIT 10;