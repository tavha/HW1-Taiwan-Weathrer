"""
Taiwan Weather Forecast Web Application (台灣一週天氣預報儀表板)
AI 創新微課程: CWA API x JSON x Python x SQLite x Streamlit
Instructor: 煥哥

Features implemented across all course steps (Steps 1-24):
- Step 3-7: CWA Open Data API fetching & Pandas structuring
- Step 8-10: SQLite (data.db / TemperatureForecasts) database management & SQL queries
- Step 11-13: Streamlit Interactive UI & Region dropdown selection
- Step 14-16: 1-Week MinT/MaxT line chart & weekly forecast table
- Step 17-19: Interactive Folium Taiwan weather map with color-coded average temperatures & Date selection
- Step 20: Code quality, idempotency (ON CONFLICT REPLACE), and robust error handling
- Step 22: AI-driven smart weather insights & clothing/activity recommendations
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium import plugins
from streamlit_folium import st_folium
import altair as alt
from datetime import datetime

# Local modules
import importlib
import database as db
import cwa_service as cwa
importlib.reload(db)
importlib.reload(cwa)

# ==========================================
# Streamlit Page Configuration
# ==========================================
st.set_page_config(
    page_title="台灣一週天氣預報 | Taiwan Weather Forecast",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Rich Modern Aesthetics)
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #f8fafc;
    }
    
    /* Hero banner styling */
    .hero-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        margin-top: 8px;
        opacity: 0.92;
        font-weight: 400;
    }
    .hero-tags {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .hero-badge {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Metric card styling */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .metric-label {
        font-size: 0.88rem;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
    }
    
    /* Status Badge */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-online {
        background-color: #dcfce7;
        color: #166534;
    }
    
    /* Map Legend Box */
    .legend-box {
        background: white;
        padding: 10px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        display: flex;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.88rem;
        font-weight: 500;
        color: #1e293b;
    }
    .legend-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }

    /* AI Advice Card */
    .ai-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 1px solid #bbf7d0;
        border-radius: 14px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Database Auto-initialization & Data Check
# ==========================================
db.init_db()

# Ensure we have data; if empty, fetch automatically
regions_in_db = db.query_distinct_regions()
if not regions_in_db:
    with st.spinner("首次啟動：正在向中央氣象署 CWA API 抓取一週天氣預報資料..."):
        try:
            cwa.fetch_and_sync_weather()
            regions_in_db = db.query_distinct_regions()
        except Exception as e:
            st.error(f"資料初始化失敗: {e}")

# ==========================================
# Sidebar Controls & Information
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=600&auto=format&fit=crop&q=80", use_container_width=True)
    st.markdown("### ⛅ 臺灣氣象控制台")
    st.caption("AI 創新微課程 Taiwan Weather Forecast")

    st.markdown("---")
    
    # API Sync Section
    st.markdown("#### 🔄 資料同步與狀態")
    st.markdown("""
        <div class="status-pill status-online">
            <span style="font-size: 10px;">🟢</span> CWA API 正常連線
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**資料來源**: 中央氣象署 (CWA Open Data)")
    st.markdown("""
    - 🛰️ **即時觀測 (含 UV)**: `O-A0003-001` (全臺自動氣象站)
    - 🔮 **一週氣象預報**: `F-D0047-091` (22 縣市未來一週)
    """)
    
    sync_btn = st.button("🚀 立即向 CWA API 同步最新預報與觀測", use_container_width=True, type="primary")
    if sync_btn:
        with st.spinner("正在向 CWA API 請求並解析最新資料 (含 O-A0003-001 實測與紫外線指數)..."):
            try:
                new_df = cwa.fetch_and_sync_weather()
                st.success(f"同步成功！已儲存 {len(new_df)} 筆歷史實測與預報紀錄至 SQLite (data.db)")
                st.rerun()
            except Exception as ex:
                st.error(f"同步失敗: {ex}")

    st.markdown("---")
    
    # Map Display Mode & Location Selection
    st.markdown("#### 📍 地圖與縣市選擇")
    map_mode = st.radio(
        "地圖呈現範圍 (Map View):",
        options=["🏙️ 全臺 22 縣市 (Every City)", "🗺️ 9 大分區 (Regional)", "🌐 全視野 (縣市+分區)"],
        index=0
    )
    
    # Order options: Cities first (categorized), then regions
    db_all_regions = db.query_distinct_regions()
    target_cities = getattr(cwa, "TARGET_CITIES", [
        "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
        "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "臺南市",
        "高雄市", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
    ])
    target_regions = getattr(cwa, "TARGET_REGIONS", [
        "北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區", "澎湖地區", "金門地區", "馬祖地區"
    ])
    cities_in_db = [c for c in target_cities if c in db_all_regions]
    regions_in_db = [r for r in target_regions if r in db_all_regions]
    other_in_db = [o for o in db_all_regions if o not in cities_in_db and o not in regions_in_db]
    available_regions = cities_in_db + regions_in_db + other_in_db
    
    if not available_regions:
        available_regions = ["臺北市", "新北市", "臺中市", "高雄市", "北部地區", "中部地區", "南部地區"]
        
    default_city_idx = available_regions.index("臺北市") if "臺北市" in available_regions else 0
    selected_region = st.selectbox(
        "選擇預報縣市/地區 (Select City/Region):",
        options=available_regions,
        index=default_city_idx
    )

    # Date Selection for Map (Step 18) - Supports Past Observations and Future Forecasts
    st.markdown("#### 📅 日期選擇 (歷史實測 / 未來預報)")
    available_dates = db.get_available_dates()
    today_str = datetime.now().strftime("%Y-%m-%d")
    if not available_dates:
        available_dates = [today_str]
        
    def format_date_option(d_str: str) -> str:
        if d_str < today_str:
            return f"📅 {d_str} (歷史實測 O-A0003-001)"
        elif d_str == today_str:
            return f"📍 {d_str} (今日實測 O-A0003-001)"
        else:
            return f"🔮 {d_str} (未來一週預報)"

    default_date_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox(
        "選擇地圖檢視日期 (Select Date):",
        options=available_dates,
        index=default_date_idx,
        format_func=format_date_option
    )

    st.markdown("---")
    st.markdown("##### 👨‍🏫 課程導師與技術棧")
    st.markdown("""
    - **技術棧**: Python · Requests · Pandas · SQLite · Streamlit · Folium
    - **資料涵蓋**: 全臺 22 縣市精確定位與氣溫色階
    - **Code Smarter, Build a Better Tomorrow!**
    """)

# ==========================================
# Main Header Banner
# ==========================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">
        <span>🌤️</span> 台灣各縣市一週天氣預報互動儀表板
    </div>
    <div class="hero-subtitle">
        全自動串接中央氣象署 Open Data API · 涵蓋全臺 22 縣市與分區 · 氣溫/濕度/PM2.5/降雨量/降雨機率/紫外線指數多元圖層 · SQLite 結構化存儲
    </div>
    <div class="hero-tags">
        <span class="hero-badge">CWA API (F-D0047-091 & O-A0003-001)</span>
        <span class="hero-badge">全臺 22 縣市精準氣象</span>
        <span class="hero-badge">6 大環境指標自由切換</span>
        <span class="hero-badge">SQLite data.db</span>
        <span class="hero-badge">Folium 地圖視覺化</span>
        <span class="hero-badge">AI 創新實作專案</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# Metric Configurations for Map Visualization
# ==========================================
METRICS_CONFIG = {
    "temp": {
        "name": "氣溫",
        "label": "🌡️ 氣溫 (°C)",
        "unit": "°C",
        "field": "temp",
        "icon": "🌡️",
        "description": "全臺各縣市平均氣溫分佈與溫層色階",
        "legend_title": "🌡️ 平均氣溫色階：",
        "legend": [
            {"color": "#2563eb", "label": "寒冷 (< 20°C)"},
            {"color": "#10b981", "label": "舒適 (20 ~ 25°C)"},
            {"color": "#f59e0b", "label": "溫暖 (25 ~ 30°C)"},
            {"color": "#ef4444", "label": "炎熱 (> 30°C)"},
        ],
        "top_label": "🔥 最高溫城市/地區",
        "bottom_label": "❄️ 最低溫城市/地區",
        "top_color": "#ef4444",
        "bottom_color": "#2563eb",
        "format": lambda v: f"{v:.1f} °C",
        "marker_format": lambda v: f"{v:.1f}°"
    },
    "humidity": {
        "name": "相對濕度",
        "label": "💧 濕度 (%)",
        "unit": "%",
        "field": "humidity",
        "icon": "💧",
        "description": "各縣市預報相對濕度 (CWA 平均相對濕度)",
        "legend_title": "💧 相對濕度色階：",
        "legend": [
            {"color": "#f59e0b", "label": "偏乾燥 (< 50%)"},
            {"color": "#10b981", "label": "適度舒適 (50 ~ 70%)"},
            {"color": "#0284c7", "label": "偏潮濕 (70 ~ 85%)"},
            {"color": "#1e3a8a", "label": "極為潮濕 (> 85%)"},
        ],
        "top_label": "💧 濕度最高城市/地區",
        "bottom_label": "🏜️ 濕度最低城市/地區",
        "top_color": "#0284c7",
        "bottom_color": "#f59e0b",
        "format": lambda v: f"{v:.1f} %",
        "marker_format": lambda v: f"{int(round(v))}%"
    },
    "pm25": {
        "name": "PM2.5",
        "label": "🌫️ PM2.5 (μg/m³)",
        "unit": "μg/m³",
        "field": "pm25",
        "icon": "🌫️",
        "description": "空氣品質細懸浮微粒 (PM2.5) 濃度分佈",
        "legend_title": "🌫️ PM2.5 指標色階：",
        "legend": [
            {"color": "#10b981", "label": "良好 (0 ~ 15.4)"},
            {"color": "#eab308", "label": "普通 (15.5 ~ 35.4)"},
            {"color": "#f97316", "label": "敏感不良 (35.5 ~ 54.4)"},
            {"color": "#ef4444", "label": "所有不良 (54.5 ~ 150)"},
            {"color": "#a855f7", "label": "危害 (> 150)"},
        ],
        "top_label": "🌫️ PM2.5 最高城市 (需留意)",
        "bottom_label": "🍃 PM2.5 最低城市 (最清新)",
        "top_color": "#ef4444",
        "bottom_color": "#10b981",
        "format": lambda v: f"{v:.1f} μg/m³",
        "marker_format": lambda v: f"{int(round(v))}μg"
    },
    "rainfall": {
        "name": "降雨量",
        "label": "🌧️ 降雨量 (mm)",
        "unit": "mm",
        "field": "rainfall",
        "icon": "🌧️",
        "description": "自動雨量站實測與預估降雨量 (mm)",
        "legend_title": "🌧️ 降雨量色階：",
        "legend": [
            {"color": "#94a3b8", "label": "無雨 (0.0 mm)"},
            {"color": "#06b6d4", "label": "微量 (0.1 ~ 5.0 mm)"},
            {"color": "#3b82f6", "label": "小雨 (5.1 ~ 15.0 mm)"},
            {"color": "#d97706", "label": "大雨 (15.1 ~ 35.0 mm)"},
            {"color": "#dc2626", "label": "豪雨 (> 35.0 mm)"},
        ],
        "top_label": "🌧️ 降雨量最多城市/地區",
        "bottom_label": "☀️ 乾爽無雨城市/地區",
        "top_color": "#3b82f6",
        "bottom_color": "#10b981",
        "format": lambda v: f"{v:.1f} mm",
        "marker_format": lambda v: f"{v:.1f}mm"
    },
    "pop": {
        "name": "降雨機率",
        "label": "☔ 降雨機率 (%)",
        "unit": "%",
        "field": "pop",
        "icon": "☔",
        "description": "中央氣象署 12小時降雨機率預報 (PoP)",
        "legend_title": "☔ 降雨機率色階：",
        "legend": [
            {"color": "#64748b", "label": "極低 (< 20%)"},
            {"color": "#06b6d4", "label": "低機率 (20 ~ 39%)"},
            {"color": "#3b82f6", "label": "可能降雨 (40 ~ 59%)"},
            {"color": "#2563eb", "label": "高機率 (60 ~ 79%)"},
            {"color": "#7c3aed", "label": "極高機率 (≥ 80%)"},
        ],
        "top_label": "☔ 降雨機率最高城市/地區",
        "bottom_label": "☀️ 降雨機率最低城市/地區",
        "top_color": "#2563eb",
        "bottom_color": "#10b981",
        "format": lambda v: f"{int(round(v))} %",
        "marker_format": lambda v: f"{int(round(v))}%"
    },
    "uvi": {
        "name": "紫外線指數",
        "label": "☀️ 紫外線指數 (UVI)",
        "unit": "",
        "field": "uvi",
        "icon": "☀️",
        "description": "中央氣象署 O-A0003-001 即時紫外線指數觀測與天氣情境推估",
        "legend_title": "☀️ 紫外線指數色階：",
        "legend": [
            {"color": "#10b981", "label": "低量 (0 ~ 2)"},
            {"color": "#eab308", "label": "中量 (3 ~ 5)"},
            {"color": "#f97316", "label": "高量 (6 ~ 7)"},
            {"color": "#ef4444", "label": "過量 (8 ~ 10)"},
            {"color": "#7c3aed", "label": "危險 (\u226511)"},
        ],
        "top_label": "☀️ 紫外線最強城市/地區",
        "bottom_label": "🌙 紫外線最低城市/地區",
        "top_color": "#ef4444",
        "bottom_color": "#10b981",
        "format": lambda v: f"{v:.1f}",
        "marker_format": lambda v: f"UV {v:.0f}"
    }
}

def get_metric_color(val: float, metric_key: str) -> str:
    """Returns hexadecimal color based on metric thresholds."""
    if metric_key == "temp":
        if val < 20.0:
            return "#2563eb"
        elif val <= 25.0:
            return "#10b981"
        elif val <= 30.0:
            return "#f59e0b"
        else:
            return "#ef4444"
    elif metric_key == "humidity":
        if val < 50.0:
            return "#f59e0b"
        elif val <= 70.0:
            return "#10b981"
        elif val <= 85.0:
            return "#0284c7"
        else:
            return "#1e3a8a"
    elif metric_key == "pm25":
        if val <= 15.4:
            return "#10b981"
        elif val <= 35.4:
            return "#eab308"
        elif val <= 54.4:
            return "#f97316"
        elif val <= 150.0:
            return "#ef4444"
        else:
            return "#a855f7"
    elif metric_key == "rainfall":
        if val <= 0.0:
            return "#94a3b8"
        elif val <= 5.0:
            return "#06b6d4"
        elif val <= 15.0:
            return "#3b82f6"
        elif val <= 35.0:
            return "#d97706"
        else:
            return "#dc2626"
    elif metric_key == "pop":
        if val < 20.0:
            return "#64748b"
        elif val < 40.0:
            return "#06b6d4"
        elif val < 60.0:
            return "#3b82f6"
        elif val < 80.0:
            return "#2563eb"
        else:
            return "#7c3aed"
    elif metric_key == "uvi":
        if val <= 2.0:
            return "#10b981"
        elif val <= 5.0:
            return "#eab308"
        elif val <= 7.0:
            return "#f97316"
        elif val <= 10.0:
            return "#ef4444"
        else:
            return "#7c3aed"
    return "#3b82f6"

def get_weather_emoji(wx: str) -> str:
    if "雷" in wx:
        return "⛈️"
    elif "雨" in wx:
        return "🌧️"
    elif "陰" in wx:
        return "☁️"
    elif "多雲" in wx:
        return "⛅"
    else:
        return "☀️"

# ==========================================
# Navigation Tabs
# ==========================================
tab_map, tab_chart, tab_table, tab_ai, tab_sql = st.tabs([
    "🗺️ 台灣地圖視覺化 (Folium)",
    "📈 縣市/地區氣象趨勢折線圖",
    "📋 詳細預報資料表",
    "🤖 AI 智慧生活指南",
    "🔍 SQL 驗證與後台教學"
])

# ==============================================================================
# TAB 1: 台灣地圖視覺化 (Folium + Streamlit, Steps 17, 18, 19)
# ==============================================================================
with tab_map:
    mode_label = "全臺 22 縣市" if "22" in map_mode else ("9 大分區" if "9" in map_mode else "全視野")
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_type_tag = "【📅 歷史實測觀測 (O-A0003-001)】" if selected_date < today_str else ("【📍 今日實測觀測 (O-A0003-001)】" if selected_date == today_str else "【🔮 未來氣象預報】")
    st.markdown(f"### 🗺️ 台灣氣象可視化地圖 — {date_type_tag} 檢視日期：`{selected_date}`（{mode_label}）")
    st.caption("結合中央氣象署 O-A0003-001 即時觀測（含紫外線指數）與 F-D0047-091 預報資料，支援點選切換【氣溫】、【濕度】、【PM2.5】、【降雨量】、【降雨機率】與【紫外線指數】六大指標熱力填色與數值呈現。")

    # Metric Switcher Bar
    st.markdown("""
    <div style="margin-bottom: 6px;">
        <span style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem;">🎯 選擇地圖熱力視覺化指標 (Map Metric Switcher)：</span>
    </div>
    """, unsafe_allow_html=True)

    selected_metric_key = st.radio(
        "選擇地圖可視化熱力圖指標 (Select Metric):",
        options=["temp", "humidity", "pm25", "rainfall", "pop", "uvi"],
        format_func=lambda k: METRICS_CONFIG[k]["label"],
        horizontal=True,
        index=0,
        label_visibility="collapsed"
    )

    current_cfg = METRICS_CONFIG[selected_metric_key]

    # Dynamic Legend Display based on selected metric
    legend_items_html = "".join([
        f'<div class="legend-item"><span class="legend-dot" style="background-color: {item["color"]};"></span> {item["label"]}</div>'
        for item in current_cfg["legend"]
    ])
    st.markdown(f"""
    <div class="legend-box">
        <span style="font-weight:700; color:#0f172a; margin-right:8px;">{current_cfg["legend_title"]}</span>
        {legend_items_html}
        <span style="margin-left:auto; font-size:0.8rem; background:#eff6ff; color:#1d4ed8; padding:3px 10px; border-radius:6px; font-weight:700; border:1px solid #bfdbfe;">
            當前熱力指標：{current_cfg['name']} ({current_cfg['unit']})
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Fetch data for selected date
    date_df = db.query_forecast_by_date(selected_date)
    
    col_map_view, col_map_info = st.columns([7, 3])
    
    with col_map_view:
        taiwan_center = [23.75, 120.95]
        m = folium.Map(
            location=taiwan_center,
            zoom_start=8,
            tiles="OpenStreetMap",
            control_scale=True
        )

        # Coordinate dictionaries with safe fallbacks
        city_coords = getattr(cwa, "CITY_COORDINATES", {})
        region_coords = getattr(cwa, "REGION_COORDINATES", {})

        # Filter items according to mode
        locations_to_plot = []
        for _, row in date_df.iterrows():
            loc_name = row["regionName"]
            min_t = float(row.get("minT", 20.0))
            max_t = float(row.get("maxT", 28.0))
            temp = float(row.get("temp", 25.0))
            avg_t = round((min_t + max_t) / 2.0, 1)
            wx = row.get("weather", "晴時多雲")
            hum = float(row.get("humidity", 70.0))
            pop_v = float(row.get("pop", 10.0))
            rain_v = float(row.get("rainfall", 0.0))
            pm_v = float(row.get("pm25", 15.0))
            uvi_v = float(row.get("uvi", 0.0))

            
            coord = city_coords.get(loc_name) or region_coords.get(loc_name)
            if not coord:
                continue

            is_city = loc_name in city_coords
            if is_city and ("22" in map_mode or "全視野" in map_mode):
                locations_to_plot.append({
                    "name": loc_name,
                    "type": "city",
                    "lat": coord["lat"],
                    "lon": coord["lon"],
                    "area": coord.get("area", ""),
                    "minT": min_t,
                    "maxT": max_t,
                    "temp": temp,
                    "avgT": avg_t,
                    "weather": wx,
                    "humidity": hum,
                    "pop": pop_v,
                    "rainfall": rain_v,
                    "pm25": pm_v,
                    "uvi": uvi_v,
                    "radius": 13
                })
            elif (not is_city) and ("9" in map_mode or "全視野" in map_mode):
                locations_to_plot.append({
                    "name": loc_name,
                    "type": "region",
                    "lat": coord["lat"],
                    "lon": coord["lon"],
                    "area": coord.get("description", ""),
                    "minT": min_t,
                    "maxT": max_t,
                    "temp": temp,
                    "avgT": avg_t,
                    "weather": wx,
                    "humidity": hum,
                    "pop": pop_v,
                    "rainfall": rain_v,
                    "pm25": pm_v,
                    "uvi": uvi_v,
                    "radius": 20
                })
                    
        # Fallback if mode list was empty
        if not locations_to_plot:
            for _, row in date_df.iterrows():
                loc_name = row["regionName"]
                coord = city_coords.get(loc_name) or region_coords.get(loc_name)
                if coord:
                    locations_to_plot.append({
                        "name": loc_name,
                        "type": "city" if loc_name in city_coords else "region",
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "area": coord.get("area", coord.get("description", "")),
                        "minT": float(row.get("minT", 20.0)),
                        "maxT": float(row.get("maxT", 28.0)),
                        "avgT": round((float(row.get("minT", 20.0)) + float(row.get("maxT", 28.0))) / 2.0, 1),
                        "weather": row.get("weather", "晴時多雲"),
                        "humidity": float(row.get("humidity", 70.0)),
                        "pop": float(row.get("pop", 10.0)),
                        "rainfall": float(row.get("rainfall", 0.0)),
                        "pm25": float(row.get("pm25", 15.0)),
                        "uvi": float(row.get("uvi", 0.0)),
                        "radius": 14
                    })

        for item in locations_to_plot:
            lat = item["lat"]
            lon = item["lon"]
            name = item["name"]
            min_t = item["minT"]
            max_t = item["maxT"]
            temp = item["temp"]
            avg_t = item["avgT"]
            wx = item["weather"]
            hum = item["humidity"]
            pop_v = item["pop"]
            rain_v = item["rainfall"]
            pm_v = item["pm25"]
            uvi_v = item.get("uvi", 0.0)

            # Current active metric values
            active_val = item[current_cfg["field"]]
            active_color = get_metric_color(active_val, selected_metric_key)
            active_label_str = current_cfg["marker_format"](active_val)

            # Colors for all individual metrics in popup
            t_color = get_metric_color(temp, "temp")
            h_color = get_metric_color(hum, "humidity")
            pm_color = get_metric_color(pm_v, "pm25")
            r_color = get_metric_color(rain_v, "rainfall")
            p_color = get_metric_color(pop_v, "pop")
            uvi_color = get_metric_color(uvi_v, "uvi")

            emoji = get_weather_emoji(wx)
            area_badge = item["area"]

            def get_hl_style(is_hl: bool) -> str:
                if is_hl:
                    return f"background: rgba(59, 130, 246, 0.12); padding: 3px 6px; border-radius: 6px; font-weight: 700; border-left: 3px solid {active_color}; margin: 2px 0;"
                return "padding: 2px 6px; margin: 1px 0;"

            popup_html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 220px; padding: 4px;">
                <div style="font-size: 15px; font-weight: 700; color: #0f172a; border-bottom: 2px solid {active_color}; padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                    <span>📍 {name}</span>
                    <span style="font-size: 11px; background: #e2e8f0; color: #334155; padding: 2px 6px; border-radius: 4px;">{area_badge}</span>
                </div>
                <div style="font-size: 13px; line-height: 1.6; color: #334155;">
                    <div style="margin-bottom: 4px;">{emoji} <b>天氣型態</b>: <span>{wx}</span></div>
                    <div style="{get_hl_style(selected_metric_key == 'temp')}">
                        🌡️ <b>平均氣溫</b>: <span style="color: {t_color}; font-weight:800;">{avg_t}°C</span> ({min_t}° ~ {max_t}°)
                    </div>
                    <div style="{get_hl_style(selected_metric_key == 'humidity')}">
                        💧 <b>相對濕度</b>: <span style="color: {h_color}; font-weight:800;">{hum}%</span>
                    </div>
                    <div style="{get_hl_style(selected_metric_key == 'pm25')}">
                        🌫️ <b>PM2.5 濃度</b>: <span style="color: {pm_color}; font-weight:800;">{pm_v} μg/m³</span>
                    </div>
                    <div style="{get_hl_style(selected_metric_key == 'rainfall')}">
                        🌧️ <b>累積降雨</b>: <span style="color: {r_color}; font-weight:800;">{rain_v} mm</span>
                    </div>
                    <div style="{get_hl_style(selected_metric_key == 'pop')}">
                        ☔ <b>降雨機率</b>: <span style="color: {p_color}; font-weight:800;">{int(round(pop_v))}%</span>
                    </div>
                    <div style="{get_hl_style(selected_metric_key == 'uvi')}">
                        ☀️ <b>紫外線指數</b>: <span style="color: {uvi_color}; font-weight:800;">UVI {uvi_v}</span>
                    </div>
                </div>
            </div>
            """

            # Add CircleMarker colored according to the selected metric
            folium.CircleMarker(
                location=[lat, lon],
                radius=item["radius"],
                popup=folium.Popup(popup_html, max_width=290),
                tooltip=f"<b>{emoji} {name}</b>: {current_cfg['name']} {active_label_str} ({wx})",
                color=active_color,
                weight=2.5,
                fill=True,
                fill_color=active_color,
                fill_opacity=0.88
            ).add_to(m)

            # Permanent label with high-contrast badge showing active metric
            offset_lat = 0.08 if item["type"] == "city" else 0.12
            short_name = name.replace("地區", "")
            folium.map.Marker(
                [lat + offset_lat, lon],
                icon=folium.DivIcon(
                    icon_size=(100, 24),
                    icon_anchor=(50, 12),
                    html=f"""
                    <div style="font-size: 11px; font-weight: 700; color: #0f172a; background: rgba(255,255,255,0.95); border: 1px solid #cbd5e1; border-radius: 4px; padding: 1px 5px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.15); white-space: nowrap;">
                        {emoji} {short_name} <span style="color:{active_color}; font-weight:800;">{active_label_str}</span>
                    </div>
                    """
                )
            ).add_to(m)

        st_folium(m, width="100%", height=560, returned_objects=[])

    with col_map_info:
        st.markdown(f"#### 📊 `{selected_date}` 【{current_cfg['name']}】數據排行")
        active_cities_df = date_df[date_df["regionName"].isin(target_cities)] if ("22" in map_mode or "全視野" in map_mode) else date_df
        if active_cities_df.empty:
            active_cities_df = date_df

        field_col = current_cfg["field"]
        if field_col == "avgT" and "avgT" not in active_cities_df.columns:
            active_cities_df = active_cities_df.copy()
            active_cities_df["avgT"] = ((active_cities_df["minT"] + active_cities_df["maxT"]) / 2.0).round(1)

        if not active_cities_df.empty and field_col in active_cities_df.columns:
            highest_row = active_cities_df.loc[active_cities_df[field_col].idxmax()]
            lowest_row = active_cities_df.loc[active_cities_df[field_col].idxmin()]
            
            top_val_str = current_cfg["format"](highest_row[field_col])
            bot_val_str = current_cfg["format"](lowest_row[field_col])

            st.markdown(f"""
            <div class="metric-card" style="margin-bottom: 12px; border-left: 4px solid {current_cfg['top_color']};">
                <div class="metric-label">{current_cfg['top_label']}</div>
                <div class="metric-val" style="color: {current_cfg['top_color']};">{top_val_str}</div>
                <div style="font-size: 0.9rem; color: #475569; margin-top: 4px;">📍 {highest_row['regionName']} ({highest_row['weather']})</div>
            </div>
            
            <div class="metric-card" style="margin-bottom: 12px; border-left: 4px solid {current_cfg['bottom_color']};">
                <div class="metric-label">{current_cfg['bottom_label']}</div>
                <div class="metric-val" style="color: {current_cfg['bottom_color']};">{bot_val_str}</div>
                <div style="font-size: 0.9rem; color: #475569; margin-top: 4px;">📍 {lowest_row['regionName']} ({lowest_row['weather']})</div>
            </div>
            """, unsafe_allow_html=True)

            # Quick City List with scroll container sorted by current metric
            st.markdown(f"##### 🏙️ 全區 {current_cfg['name']} 清單 ({len(active_cities_df)} 處)")
            with st.container(height=260):
                sorted_df = active_cities_df.sort_values(by=field_col, ascending=False)
                for _, r in sorted_df.iterrows():
                    r_name = r["regionName"]
                    r_val = r[field_col]
                    r_val_str = current_cfg["format"](r_val)
                    r_wx = r.get("weather", "")
                    dot_c = get_metric_color(r_val, selected_metric_key)
                    wx_ico = get_weather_emoji(r_wx)
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding: 5px 0; border-bottom: 1px dashed #e2e8f0; font-size: 0.88rem;">
                        <span><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{dot_c}; margin-right:6px;"></span>{wx_ico} <b>{r_name}</b></span>
                        <span style="color:{dot_c}; font-weight:700;">{r_val_str}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("尚無該日期之氣象預報資料。")

# ==============================================================================
# TAB 2: 地區氣象趨勢折線圖 (Steps 13, 14, 15, 16)
# ==============================================================================
with tab_chart:
    st.markdown(f"### 📈 【{selected_region}】歷史實測與未來氣象走勢分析")
    st.caption("無縫整合中央氣象署 O-A0003-001 即時觀測與未來預報，自由切換氣溫、濕度、PM2.5、降雨量、降雨機率與紫外線指數連續趨勢。")

    # Query region forecast from SQLite (Step 12)
    df_region = db.query_forecast_by_region(selected_region)

    if not df_region.empty:
        # Key Summary Metrics
        max_week_temp = df_region["maxT"].max()
        min_week_temp = df_region["minT"].min()
        avg_week_humidity = round(df_region["humidity"].mean(), 1) if "humidity" in df_region else 70.0
        avg_week_pm25 = round(df_region["pm25"].mean(), 1) if "pm25" in df_region else 18.0
        max_week_rain = round(df_region["rainfall"].max(), 1) if "rainfall" in df_region else 0.0
        max_week_pop = int(round(df_region["pop"].max())) if "pop" in df_region else 20
        max_week_uvi = round(df_region["uvi"].max(), 1) if "uvi" in df_region else 0.0

        c1, c2, c3, c4, c5= st.columns(5)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🌡️ 本週氣溫區間</div>
                <div class="metric-val" style="color: #ef4444; font-size: 1.5rem;">{min_week_temp}°C ~ {max_week_temp}°C</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💧 本週平均濕度</div>
                <div class="metric-val" style="color: #0284c7; font-size: 1.5rem;">{avg_week_humidity} %</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🌫️ 平均 PM2.5 濃度</div>
                <div class="metric-val" style="color: #f59e0b; font-size: 1.5rem;">{avg_week_pm25} μg/m³</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">☔ 最高降雨量 / 機率</div>
                <div class="metric-val" style="color: #3b82f6; font-size: 1.5rem;">{max_week_rain}mm / {max_week_pop}%</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">☀️ 本週最高紫外線指數</div>
                <div class="metric-val" style="color: #f97316; font-size: 1.5rem;">UVI {max_week_uvi}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Trend Chart Metric Switcher
        chart_metric_opt = st.radio(
            "選擇欲繪製的走勢圖指標 (Select Trend Chart Metric):",
            options=["氣溫趨勢 (最高溫 / 最低溫)", "相對濕度 (%)", "PM2.5 細懸浮微粒 (μg/m³)", "累積降雨量預測 (mm)", "降雨機率預報 (%)", "紫外線指數 (UVI)"],
            horizontal=True,
            index=0
        )

        if chart_metric_opt == "氣溫趨勢 (最高溫 / 最低溫)":
            chart_data = df_region.melt(
                id_vars=["dataDate"],
                value_vars=["maxT", "minT"],
                var_name="指標",
                value_name="氣溫"
            )
            chart_data["指標名稱"] = chart_data["指標"].map({
                "maxT": "最高氣溫 (MaxT)",
                "minT": "最低氣溫 (MinT)"
            })
            base_chart = alt.Chart(chart_data).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("氣溫:Q", title="氣溫 (°C)", scale=alt.Scale(domain=[int(min_week_temp - 3), int(max_week_temp + 3)])),
                color=alt.Color(
                    "指標名稱:N",
                    title="溫度類型",
                    scale=alt.Scale(
                        domain=["最高氣溫 (MaxT)", "最低氣溫 (MinT)"],
                        range=["#ef4444", "#3b82f6"]
                    ),
                    legend=alt.Legend(orient="top", titleFontWeight="bold")
                )
            )
            lines = base_chart.mark_line(size=3, interpolate="monotone")
            points = base_chart.mark_circle(size=70)
            labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
                text=alt.Text("氣溫:Q", format=".1f")
            )
            final_chart = (lines + points + labels).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週最高與最低氣溫走勢圖",
                    subtitle="資料來源：中央氣象署 Open Data (F-D0047-091 / F-C0032-003)",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        elif chart_metric_opt == "相對濕度 (%)":
            base_chart = alt.Chart(df_region).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("humidity:Q", title="相對濕度 (%)", scale=alt.Scale(domain=[40, 100])),
                color=alt.value("#0284c7")
            )
            lines = base_chart.mark_line(size=3, interpolate="monotone")
            points = base_chart.mark_circle(size=70)
            labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
                text=alt.Text("humidity:Q", format=".1f")
            )
            final_chart = (lines + points + labels).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週相對濕度 (%) 走勢圖",
                    subtitle="資料來源：中央氣象署 Open Data 平均相對濕度",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        elif chart_metric_opt == "PM2.5 細懸浮微粒 (μg/m³)":
            base_chart = alt.Chart(df_region).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("pm25:Q", title="PM2.5 (μg/m³)", scale=alt.Scale(domain=[0, max(50, int(df_region['pm25'].max() + 10))])),
                color=alt.value("#f59e0b")
            )
            lines = base_chart.mark_line(size=3, interpolate="monotone")
            points = base_chart.mark_circle(size=70)
            labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
                text=alt.Text("pm25:Q", format=".1f")
            )
            final_chart = (lines + points + labels).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週 PM2.5 細懸浮微粒走勢圖",
                    subtitle="環境部空氣品質監測與環境特徵模型",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        elif chart_metric_opt == "累積降雨量預測 (mm)":
            base_chart = alt.Chart(df_region).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("rainfall:Q", title="降雨量 (mm)", scale=alt.Scale(domain=[0, max(15, int(df_region['rainfall'].max() + 5))])),
                color=alt.value("#06b6d4")
            )
            bars = base_chart.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=30)
            labels = base_chart.mark_text(dy=-10, fontWeight="bold").encode(
                text=alt.Text("rainfall:Q", format=".1f")
            )
            final_chart = (bars + labels).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週累積降雨量預測 (mm)",
                    subtitle="自動雨量站觀測與天氣情境估計",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        elif chart_metric_opt == "降雨機率預報 (%)":
            base_chart = alt.Chart(df_region).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("pop:Q", title="降雨機率 (%)", scale=alt.Scale(domain=[0, 100])),
                color=alt.value("#6366f1")
            )
            lines = base_chart.mark_line(size=3, interpolate="monotone")
            points = base_chart.mark_circle(size=70)
            labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
                text=alt.Text("pop:Q", format=".0f")
            )
            final_chart = (lines + points + labels).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週 12小時降雨機率 (PoP %) 走勢圖",
                    subtitle="資料來源：中央氣象署 Open Data 12小時降雨機率",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        elif chart_metric_opt == "紫外線指數 (UVI)":
            base_chart = alt.Chart(df_region).encode(
                x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
                y=alt.Y("uvi:Q", title="紫外線指數 (UVI)", scale=alt.Scale(domain=[0, max(12, int(df_region['uvi'].max() + 2))])),
                color=alt.value("#f97316")
            )
            lines = base_chart.mark_line(size=3, interpolate="monotone")
            points = base_chart.mark_circle(size=70)
            labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
                text=alt.Text("uvi:Q", format=".1f")
            )
            # Add danger threshold line at UVI 8
            threshold = alt.Chart(pd.DataFrame({'y': [8]})).mark_rule(
                color='#ef4444', strokeDash=[6, 4], strokeWidth=2
            ).encode(y='y:Q')
            final_chart = (lines + points + labels + threshold).properties(
                height=380,
                title=alt.TitleParams(
                    text=f"{selected_region} 未來一週紫外線指數 (UVI) 走勢圖",
                    subtitle="資料來源：中央氣象署 O-A0003-001 即時觀測與天氣情境推估 (紅線 = UVI 8 過量級警戒)",
                    fontSize=16
                )
            ).interactive()
            st.altair_chart(final_chart, use_container_width=True)

        # 顯示完整資料表格 (含 5 大指標)
        st.markdown("#### 📅 一週多元氣象數據表")
        display_df = df_region.copy()
        display_df["平均溫 (°C)"] = ((display_df["minT"] + display_df["maxT"]) / 2).round(1)
        display_df["日溫差 (°C)"] = (display_df["maxT"] - display_df["minT"]).round(1)
        display_df = display_df.rename(columns={
            "dataDate": "預報日期 (Date)",
            "minT": "最低溫 (°C)",
            "maxT": "最高溫 (°C)",
            "humidity": "相對濕度 (%)",
            "pop": "降雨機率 (%)",
            "rainfall": "降雨量 (mm)",
            "pm25": "PM2.5 (μg/m³)",
            "uvi": "紫外線指數 (UVI)",
            "weather": "天氣現象 (Wx)"
        })
        
        st.dataframe(
            display_df[[
                "預報日期 (Date)", "最低溫 (°C)", "最高溫 (°C)", "平均溫 (°C)", "日溫差 (°C)", 
                "相對濕度 (%)", "降雨機率 (%)", "降雨量 (mm)", "PM2.5 (μg/m³)", "紫外線指數 (UVI)", "天氣現象 (Wx)"
            ]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning(f"目前資料庫中查無 {selected_region} 的氣溫資料，請點擊側邊欄「立即向 CWA API 同步」按鈕。")

# ==============================================================================
# TAB 3: 詳細預報資料表 & 跨區對比 (Step 15 & 16)
# ==============================================================================
with tab_table:
    st.markdown("### 📋 全臺各地區預報完整資料庫")
    st.caption("查詢自 SQLite 資料庫 `data.db` 中的 `TemperatureForecasts` 資料表（涵蓋氣溫、濕度、降雨量、降雨機率、PM2.5 與紫外線指數）。")

    all_df = db.query_all_forecasts()
    
    col_filter1, col_filter2 = st.columns([1, 1])
    with col_filter1:
        region_filter = st.multiselect("篩選地區:", options=available_regions, default=available_regions[:4])
    with col_filter2:
        date_filter = st.multiselect("篩選日期:", options=available_dates, default=available_dates[:4])

    filtered_df = all_df.copy()
    if region_filter:
        filtered_df = filtered_df[filtered_df["regionName"].isin(region_filter)]
    if date_filter:
        filtered_df = filtered_df[filtered_df["dataDate"].isin(date_filter)]

    rename_cols = {
        "id": "編號 (ID)",
        "regionName": "地區名稱 (Region)",
        "dataDate": "日期 (Date)",
        "minT": "最低溫 (°C)",
        "maxT": "最高溫 (°C)",
        "humidity": "相對濕度 (%)",
        "pop": "降雨機率 (%)",
        "rainfall": "降雨量 (mm)",
        "pm25": "PM2.5 (μg/m³)",
        "uvi": "紫外線指數 (UVI)",
        "weather": "天氣現象",
        "created_at": "同步時間"
    }

    cols_order = [c for c in [
        "編號 (ID)", "地區名稱 (Region)", "日期 (Date)", "最低溫 (°C)", "最高溫 (°C)", 
        "相對濕度 (%)", "降雨機率 (%)", "降雨量 (mm)", "PM2.5 (μg/m³)", "紫外線指數 (UVI)", "天氣現象", "同步時間"
    ] if c in [rename_cols.get(k, k) for k in filtered_df.columns]]

    renamed_df = filtered_df.rename(columns=rename_cols)
    st.dataframe(
        renamed_df[cols_order] if cols_order else renamed_df,
        use_container_width=True,
        hide_index=True
    )

    # Download CSV button
    csv_bytes = renamed_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下載篩選後氣象資料 (CSV)",
        data=csv_bytes,
        file_name="taiwan_weather_forecast.csv",
        mime="text/csv"
    )

# ==============================================================================
# TAB 4: AI 智慧生活指南 (Step 22: 延伸應用與想法)
# ==============================================================================
with tab_ai:
    st.markdown("### 🤖 AI 氣象分析與智慧生活建議")
    st.caption("Step 22: 結合氣象與環境大數據（氣溫、濕度、PM2.5、降雨量、降雨機率、紫外線指數），自動生成個人化生活指南。")

    region_data = date_df[date_df["regionName"] == selected_region]
    print(region_data)
    if not region_data.empty:
        today_data = region_data.iloc[0]
        today_date = today_data["dataDate"]
        today_min = float(today_data["minT"])
        today_max = float(today_data["maxT"])
        today_diff = today_max - today_min
        today_wx = today_data["weather"]
        today_hum = float(today_data.get("humidity", 70.0))
        today_pop = float(today_data.get("pop", 10.0))
        today_rain = float(today_data.get("rainfall", 0.0))
        today_pm25 = float(today_data.get("pm25", 15.0))
        today_uvi = float(today_data.get("uvi", 0.0))

        # 1. Clothing advice
        clothing_text = ""
        clothing_icon = "👕"
        if today_max >= 30:
            clothing_text = "氣溫偏高炎熱，建議著輕便透氣短袖、短褲或排汗衫，戶外活動務必防曬防中暑。"
            clothing_icon = "🎽"
        elif today_max >= 24:
            clothing_text = "氣候溫和宜人，建議著短袖上衣，早晚或冷氣房內備一件薄外套抵禦溫差。"
            clothing_icon = "👕"
        elif today_max >= 18:
            clothing_text = "體感略涼，建議搭配長袖襯衫、帽T或防風夾克，早晚通勤注意添衣保暖。"
            clothing_icon = "🧥"
        else:
            clothing_text = "氣溫偏低寒冷，建議採洋蔥式穿法，著厚毛衣、防風大衣或輕羽絨外套。"
            clothing_icon = "🧣"

        # 2. Rain & Umbrella advice
        umbrella_text = ""
        umbrella_icon = "☀️"
        if today_pop >= 70 or today_rain >= 10.0:
            umbrella_text = f"降雨機率高達 {int(round(today_pop))}%（預測累積雨量 {today_rain} mm），出門務必攜帶長傘或雨衣，留意路面濕滑。"
            umbrella_icon = "⛈️"
        elif today_pop >= 40 or today_rain > 0.5:
            umbrella_text = f"降雨機率約 {int(round(today_pop))}%（雨量估計 {today_rain} mm），外出建議隨身放一把折疊傘，以備不時之需。"
            umbrella_icon = "☔"
        elif "陰" in today_wx:
            umbrella_text = f"雲層偏厚陰天（降雨機率 {int(round(today_pop))}%），偶有零星微雨，戶外活動建議備傘。"
            umbrella_icon = "⛅"
        else:
            umbrella_text = f"天氣晴朗（降雨機率僅 {int(round(today_pop))}%），無明顯降雨，戶外活動與洗曬衣物皆非常理想！"
            umbrella_icon = "☀️"

        # 3. PM2.5 & Air Quality advice
        pm_text = ""
        pm_icon = "🍃"
        if today_pm25 <= 15.4:
            pm_text = f"PM2.5 指標良好（{today_pm25} μg/m³），空氣清新純淨，適合開窗通風與進行各類戶外跑步、運動。"
            pm_icon = "🟢"
        elif today_pm25 <= 35.4:
            pm_text = f"PM2.5 為普通等級（{today_pm25} μg/m³），一般民眾可正常戶外活動，極敏感族群可視情況配戴一般防護口罩。"
            pm_icon = "🟡"
        elif today_pm25 <= 54.4:
            pm_text = f"PM2.5 達敏感族群不健康橘色預警（{today_pm25} μg/m³），孩童、長輩及呼吸道敏感者建議減少戶外劇烈運動並配戴口罩。"
            pm_icon = "🟠"
        else:
            pm_text = f"PM2.5 達紅色警戒以上（{today_pm25} μg/m³），空氣品質不佳，建議緊閉門窗、開啟空氣清淨機並配戴高防護口罩。"
            pm_icon = "🔴"

        # 4. Humidity & Living Environment advice
        hum_text = ""
        hum_icon = "💧"
        if today_hum >= 85.0:
            hum_text = f"相對濕度高達 {today_hum}%，體感濕黏易悶熱或潮濕，建議開啟除濕機維持在 55%~60%，防止衣物與牆面發霉。"
            hum_icon = "💦"
        elif today_hum >= 65.0:
            hum_text = f"相對濕度為 {today_hum}%，水氣適中，適時開窗讓空氣流通即可維持室內舒適體感。"
            hum_icon = "💧"
        elif today_hum >= 45.0:
            hum_text = f"相對濕度為 {today_hum}%，環境清爽舒適，人體最適宜濕度區間，晾曬衣物乾燥迅速。"
            hum_icon = "🍃"
        else:
            hum_text = f"相對濕度偏低（{today_hum}%），空氣較為乾燥，請留意肌膚保濕並多飲水，敏感者可使用加濕器。"
            hum_icon = "🏜️"

        # 5. UV Index advice (紫外線指數防護建議)
        uv_text = ""
        uv_icon = "☀️"
        if today_uvi >= 11.0:
            uv_text = f"紫外線指數達危險級（UVI {today_uvi}），極短時間即可造成皮膚灼傷。建議避免上午 10 時至下午 2 時外出，外出必須塗抹 SPF50+ 防曬乳、穿著長袖深色衣物、戴寬邊帽與 UV400 太陽眼鏡。"
            uv_icon = "🔴"
        elif today_uvi >= 8.0:
            uv_text = f"紫外線指數過量（UVI {today_uvi}），戶外 15~20 分鐘即可能曬傷。建議塗抹 SPF50 防曬乳，戴帽子與太陽眼鏡，並盡量在有遮蔭處活動，中午前後減少日照暴露。"
            uv_icon = "🟠"
        elif today_uvi >= 6.0:
            uv_text = f"紫外線指數偏高（UVI {today_uvi}），建議外出時塗抹 SPF30 以上防曬乳，配戴太陽眼鏡與帽子，避免長時間直曬。"
            uv_icon = "🟡"
        elif today_uvi >= 3.0:
            uv_text = f"紫外線指數中量（UVI {today_uvi}），一般活動可正常進行，長時間戶外運動建議適當防曬。"
            uv_icon = "🟢"
        else:
            uv_text = f"紫外線指數低（UVI {today_uvi}），紫外線輻射微弱，無需特別防護。"
            uv_icon = "🟢"

        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.markdown(f"""
            <div class="ai-card" style="margin-bottom: 14px;">
                <h4 style="margin:0 0 8px 0; color:#166534;">{clothing_icon} 穿衣穿搭與溫差指南</h4>
                <div style="font-size: 0.92rem; color:#14532d; line-height: 1.6;">
                    <b>預報溫層</b>：{today_min}°C ~ {today_max}°C（日夜溫差 {today_diff:.1f}°C）<br>
                    {clothing_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="ai-card" style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-color: #fde68a; margin-bottom: 14px;">
                <h4 style="margin:0 0 8px 0; color:#92400e;">{pm_icon} PM2.5 空氣品質與健康防護</h4>
                <div style="font-size: 0.92rem; color:#78350f; line-height: 1.6;">
                    <b>PM2.5 濃度</b>：{today_pm25} μg/m³<br>
                    {pm_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_ai2:
            st.markdown(f"""
            <div class="ai-card" style="background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%); border-color: #bfdbfe; margin-bottom: 14px;">
                <h4 style="margin:0 0 8px 0; color:#1e40af;">{umbrella_icon} 出行、降雨量與雨具建議</h4>
                <div style="font-size: 0.92rem; color:#1e3a8a; line-height: 1.6;">
                    <b>天候型態</b>：{today_wx}（降雨機率 {int(round(today_pop))}% · 雨量 {today_rain} mm）<br>
                    {umbrella_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="ai-card" style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-color: #bbf7d0; margin-bottom: 14px;">
                <h4 style="margin:0 0 8px 0; color:#15803d;">{hum_icon} 相對濕度與居家環境建議</h4>
                <div style="font-size: 0.92rem; color:#166534; line-height: 1.6;">
                    <b>相對濕度</b>：{today_hum}%<br>
                    {hum_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # UV Index advice card (full width)
        st.markdown(f"""
        <div class="ai-card" style="background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); border-color: #fed7aa; margin-bottom: 14px;">
            <h4 style="margin:0 0 8px 0; color:#9a3412;">{uv_icon} 紫外線指數防護與戶外活動建議</h4>
            <div style="font-size: 0.92rem; color:#7c2d12; line-height: 1.6;">
                <b>紫外線指數</b>：UVI {today_uvi}（資料來源：O-A0003-001 即時觀測）<br>
                {uv_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 💡 未來延伸應用發想 (Step 22)")
        st.markdown("""
        - 📱 **LINE Bot 自動推播**：串接 LINE Messaging API，每日早晨 7:30 自動將當日降雨機率、PM2.5 與穿衣指南推播給使用者。
        - 🚗 **智慧旅遊路線規劃**：根據各區天氣、降雨量與空品指標，推薦晴朗清新區域的戶外景點，下雨區域則推薦室內博物館或特色咖啡廳。
        - 🌾 **智慧農業防災預警**：針對劇烈降溫（寒害）、連續豪大雨或極端濕度發送農民預警簡訊，提早進行溫室通風與作物防護。
        """)

# ==============================================================================
# TAB 5: SQL 驗證與後台教學 (Steps 8, 9, 10, 20)
# ==============================================================================
with tab_sql:
    st.markdown("### 🔍 SQL 資料庫驗證與架構解析 (Steps 8, 9, 10 & 20)")
    st.caption("直觀驗證課程中學到的 SQLite 結構與 SQL 查詢語句。")

    st.markdown("#### 1. 資料庫設計 Schema (Step 9)")
    st.code("""
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    minT REAL NOT NULL,
    maxT REAL NOT NULL,
    humidity REAL DEFAULT 70.0,
    pop REAL DEFAULT 0.0,
    rainfall REAL DEFAULT 0.0,
    pm25 REAL DEFAULT 15.0,
    uvi REAL DEFAULT 0.0,
    weather TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
);
    """, language="sql")

    st.markdown("#### 2. SQL 互動式查詢驗證 (Step 10)")
    user_query = st.text_input(
        "輸入欲執行的 SQL 查詢語法：",
        value=f'SELECT * FROM TemperatureForecasts WHERE regionName = "{selected_region}" LIMIT 7;'
    )

    if user_query:
        try:
            conn = db.get_connection()
            result_df = pd.read_sql_query(user_query, conn)
            conn.close()
            st.success(f"查詢成功！共返回 {len(result_df)} 筆結果：")
            st.dataframe(result_df, use_container_width=True)
        except Exception as sql_err:
            st.error(f"SQL 查詢執行出錯: {sql_err}")

    st.markdown("#### 3. 程式碼品質與架構優化 (Step 20)")
    st.markdown("""
    - ✅ **即時觀測與紫外線指數整合 (O-A0003-001)**：串接中央氣象署全臺自動氣象站即時觀測資料（含紫外線指數 UVIndex），完整儲存當日極值與過去歷史觀測紀錄。
    - ✅ **精簡雙 API 架構**：僅使用 `F-D0047-091`（22 縣市一週預報）與 `O-A0003-001`（即時觀測含 UV），9 大分區數據由縣市資料聚合產生，降低 API 呼叫次數。
    - ✅ **重複執行不重複插入**：使用 `UNIQUE(regionName, dataDate) ON CONFLICT REPLACE`，無論執行多少次資料同步都不會產生重複垃圾資料，並可隨時間無損累積歷史資料庫。
    - ✅ **錯誤處理機制**：透過 `try-except` 捕獲網路連線超時、SSL 憑證問題與 JSON 解析異常，並具備自動回退機制。
    - ✅ **模組化分工**：
      - `database.py`：專職負責 SQLite 初始化與資料庫查詢封裝，具備自動 Schema 欄位遷移功能（含 uvi 欄位）。
      - `cwa_service.py`：專職負責氣象署 API（O-A0003-001 / F-D0047-091）串接與數據清洗。
      - `app.py`：專職負責前端 Streamlit 視覺化呈現、Folium 互動地圖與 6 大指標切換。
    - ✅ **良好繁體中文註解**：清晰呈現各步驟邏輯，便於代碼維護與學習。
    """)

# ==========================================
# Footer
# ==========================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.88rem; padding: 1rem 0;">
    AI 創新微課程 Taiwan Weather Forecast · 資料來源：中華民國交通部中央氣象署 (CWA Open Data)<br>
    Code Smarter, Build a Better Tomorrow! · 煥哥 與你一起用 AI 寫程式探索更大的世界
</div>
""", unsafe_allow_html=True)
