import pandas as pd
from sqlalchemy import create_engine
import time

# 数据库连接配置
# 数据库配置信息
DB_USER = "root"
DB_PASSWORD = "000000"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "database"

# 构造连接字符串
DB_CONFIG = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_CONFIG)


def perform_high_speed_aggregation():
    start_time = time.time()
    print("开始从数据库提取并聚合160万条数据...")

    query = "SELECT airline_name, month, DepDel15, DepDelayMinutes, Is_Cancelled, CarrierDelay, WeatherDelay, NASDelay, LateAircraftDelay FROM v_flight_performance_analysis"

    chunks = []
    for chunk in pd.read_sql(query, engine, chunksize=200000):
        agg_chunk = chunk.groupby(['airline_name', 'month']).agg({
            'DepDel15': ['count', 'sum'],
            'DepDelayMinutes': 'mean',
            'Is_Cancelled': 'sum',
            'CarrierDelay': 'sum',
            'WeatherDelay': 'sum',
            'NASDelay': 'sum',
            'LateAircraftDelay': 'sum'
        })
        chunks.append(agg_chunk)

    final_stats = pd.concat(chunks).groupby(level=[0, 1]).sum()
    final_stats.columns = ['_'.join(col).strip() for col in final_stats.columns.values]
    final_stats = final_stats.reset_index()
    final_stats['on_time_rate'] = 1 - (final_stats['DepDel15_sum'] / final_stats['DepDel15_count'])

    final_stats.to_csv('airline_monthly_performance.csv', index=False)
    print(f"航司数据聚合完成！时间: {time.time() - start_time:.2f}秒")


def aggregate_airport_data():
    start_time = time.time()
    print("开始聚合多维地理分析数据（支持实时筛选）...")

    # 关键修改：在 SQL 中保留 airline_name 和 month 维度
    query = """
    SELECT 
        airline_name,
        month,
        origin_city,
        COUNT(*) as total_flights,
        SUM(DepDel15) as delayed_flights
    FROM v_flight_performance_analysis
    GROUP BY airline_name, month, origin_city
    """
    try:
        airport_stats = pd.read_sql(query, engine)

        # 机场经纬度坐标映射
        coords = {
            'Atlanta, GA': [33.6407, -84.4277], 'Chicago, IL': [41.9742, -87.9073],
            'Dallas/Fort Worth, TX': [32.8998, -97.0403], 'Denver, CO': [39.8561, -104.6737],
            'San Francisco, CA': [37.6213, -122.3790], 'New York, NY': [40.6413, -73.7781],
            'Los Angeles, CA': [33.9416, -118.4085], 'Seattle, WA': [47.4502, -122.3088],
            'Houston, TX': [29.9804, -95.3397], 'Phoenix, AZ': [33.4342, -112.0081],
            'Las Vegas, NV': [36.0840, -115.1537], 'Charlotte, NC': [35.2140, -80.9431]
        }

        airport_stats['lat'] = airport_stats['origin_city'].map(lambda x: coords.get(x, [None])[0])
        airport_stats['lon'] = airport_stats['origin_city'].map(lambda x: coords.get(x, [None, None])[1])
        airport_stats = airport_stats.dropna(subset=['lat', 'lon'])

        # 保存包含维度的多维地理数据
        airport_stats.to_csv('airport_performance.csv', index=False)
        print(f"多维地理数据生成完成！时间: {time.time() - start_time:.2f}秒")
    except Exception as e:
        print(f"聚合机场数据时出错: {e}")


if __name__ == "__main__":
    perform_high_speed_aggregation()
    aggregate_airport_data()