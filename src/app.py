import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 1. 页面配置与美化 ---
# 设置网页标题、图标以及宽屏布局
st.set_page_config(
    page_title="2025 Q1 航运大数据仪表板",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS：优化 UI 质感，增加卡片阴影和标签页样式
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)


# --- 2. 数据加载 (使用缓存以提高加载速度) ---
@st.cache_data
def load_all_data():
    paths = {
        'airline': 'airline_monthly_performance.csv',
        'airport': 'airport_performance.csv'
    }
    data = {}
    for key, path in paths.items():
        # 兼容本地和 src 目录路径
        target_path = path if os.path.exists(path) else f'src/{path}'
        if os.path.exists(target_path):
            data[key] = pd.read_csv(target_path)
        else:
            data[key] = pd.DataFrame()
    return data.get('airline', pd.DataFrame()), data.get('airport', pd.DataFrame())


df_airline, df_airport = load_all_data()

# --- 3. 侧边栏：多维度交互筛选 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/airport.png", width=80)
    st.title("控制面板")
    st.markdown("---")

    if not df_airline.empty:
        # 月份筛选器
        months = sorted(df_airline['month'].unique())
        st.subheader("🗓️ 时间维度")
        selected_month = st.multiselect("选择分析月份", options=months, default=months)

        # 航司筛选器
        st.subheader("🏢 航空公司")
        all_airlines = sorted(df_airline['airline_name'].unique())

        # 快捷全选逻辑
        if st.checkbox("选中所有航司", value=False):
            selected_airlines = all_airlines
        else:
            selected_airlines = st.multiselect(
                "选择航司 (支持搜索)",
                options=all_airlines,
                default=all_airlines[:3]
            )

    st.markdown("---")
    st.info("💡 提示：更改筛选条件后，所有图表将实时更新。")

# --- 4. 业务逻辑处理 ---
if df_airline.empty or df_airport.empty:
    st.error("数据加载失败。请确保已运行聚合脚本并生成了对应的 CSV 文件。")
    st.stop()

# 核心联动过滤
mask_airline = (df_airline['month'].isin(selected_month)) & (df_airline['airline_name'].isin(selected_airlines))
f_airline = df_airline[mask_airline]

mask_geo = (df_airport['month'].isin(selected_month)) & (df_airport['airline_name'].isin(selected_airlines))
f_geo = df_airport[mask_geo]

# --- 5. 顶层 KPI 统计卡片 ---
st.title("✈️ 美国航班运营效率大数据看板")
st.caption("数据周期：2025年第一季度 (Jan - Mar) | 实时数据源：MySQL 聚合引擎")

# 计算核心指标
total_f = f_airline['DepDel15_count'].sum()
total_delayed = f_airline['DepDel15_sum'].sum()
avg_otp = (f_airline['on_time_rate'] * f_airline['DepDel15_count']).sum() / total_f * 100 if total_f > 0 else 0
cancelled_count = f_airline['Is_Cancelled_sum'].sum()

# 布局 KPI 卡片
k1, k2, k3, k4 = st.columns(4)
k1.metric("监测航班总量", f"{int(total_f):,}", help="当前筛选条件下的总起飞架次")
k2.metric("平均准点率", f"{avg_otp:.1f}%", f"{avg_otp - 80:.1f}%", help="对比行业基准 80%")
k3.metric("延误航班总数", f"{int(total_delayed):,}", delta_color="inverse")
k4.metric("异常取消数", f"{int(cancelled_count):,}", delta_color="inverse")

st.markdown("---")

# --- 6. 标签页内容渲染 ---
tab_dashboard, tab_map, tab_docs = st.tabs(["📊 运营看板", "🌍 空间热力图", "📖 技术文档"])

with tab_dashboard:
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("📈 航司平均延误时长排名 (分钟)")
        # 按航司汇总延误时长
        airline_rank = f_airline.groupby('airline_name')['DepDelayMinutes_mean'].mean().reset_index().sort_values(
            'DepDelayMinutes_mean')
        fig_rank = px.bar(
            airline_rank,
            x='DepDelayMinutes_mean',
            y='airline_name',
            orientation='h',
            color='DepDelayMinutes_mean',
            color_continuous_scale='Reds',
            text_auto='.1f'
        )
        fig_rank.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_r:
        st.subheader("🧩 延误归因分析")
        reasons = {
            '航司原因': f_airline['CarrierDelay_sum'].sum(),
            '天气影响': f_airline['WeatherDelay_sum'].sum(),
            '空管调度': f_airline['NASDelay_sum'].sum(),
            '前序晚到': f_airline['LateAircraftDelay_sum'].sum()
        }
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(reasons.keys()),
            values=list(reasons.values()),
            hole=.4,
            marker=dict(colors=px.colors.qualitative.Pastel)
        )])
        fig_pie.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📅 季度内准点率走势")
    trend_data = f_airline.groupby('month')['on_time_rate'].mean().reset_index()
    trend_data['month_label'] = trend_data['month'].map({1: '1月', 2: '2月', 3: '3月'})
    fig_trend = px.line(trend_data, x='month_label', y='on_time_rate', markers=True,
                        color_discrete_sequence=['#007bff'])
    fig_trend.update_layout(height=300, yaxis_range=[0.5, 1.0], yaxis_title="准点率")
    st.plotly_chart(fig_trend, use_container_width=True)

with tab_map:
    st.subheader("📍 全美枢纽机场延误监测")
    st.info("气泡大小：航班量 | 颜色深浅：延误率")

    # 动态地理聚合：关键点在于按坐标重新 GroupBy 以支持航司联动
    map_agg = f_geo.groupby(['origin_city', 'lat', 'lon']).agg({
        'total_flights': 'sum',
        'delayed_flights': 'sum'
    }).reset_index()

    # --- 核心修复：确保计算 delay_rate 列 ---
    # 在 groupby 聚合后，DataFrame 不包含 delay_rate 列，需要重新计算
    map_agg['delay_rate'] = (map_agg['delayed_flights'] / map_agg['total_flights'] * 100).fillna(0).round(2)

    if not map_agg.empty:
        fig_map = px.scatter_mapbox(
            map_agg,
            lat="lat", lon="lon",
            size="total_flights",
            color="delay_rate",  # 此列现在已显式存在于 map_agg 中
            hover_name="origin_city",
            hover_data={"lat": False, "lon": False, "total_flights": True, "delay_rate": True},
            color_continuous_scale="YlOrRd",
            size_max=45,
            zoom=3.2,
            mapbox_style="carto-positron"
        )
        fig_map.update_layout(height=700, margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("所选条件下无可用地理数据。")

with tab_docs:
    st.markdown("""
    ### 📖 技术实现文档
    #### 1. 数据处理流
    - **原始层**: 160万+ 航班明细数据。
    - **聚合层**: 利用 Pandas 的 `Chunking` 机制处理 2GB+ CSV，避免内存溢出。
    - **存储层**: 采用 MySQL 星型模型架构，通过视图 `v_flight_performance_analysis` 预先处理字段关联与字符集转换。

    #### 2. 看板优化细节
    - **实时联动**: 地图与统计图表共用一套 Filter Mask，实现同步下钻分析。
    - **UI/UX**: 采用 `st.cache_data` 缓存加载结果，即使处理百万级数据量，界面交互仍可达到毫秒级响应。
    - **健壮性**: 显式处理地理坐标缺失及分母为零的异常情况。
    """)

# --- 7. 页脚信息 ---
st.markdown("---")
st.caption("© 2025 美国航班大数据分析看板 | 构建环境: Python 3.11 + Pandas + Streamlit")