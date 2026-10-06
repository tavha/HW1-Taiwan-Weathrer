"""
Database management module for Taiwan Weather Forecast
Handles SQLite database initialization, table creation, and queries.
Corresponds to Steps 8, 9, 10, and 12 in the course workflow.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

DB_FILE = "data.db"

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DB_FILE) -> None:
    """
    Step 8 & 9: Initialize SQLite database and create TemperatureForecasts table.
    Ensures idempotency with UNIQUE(regionName, dataDate) ON CONFLICT REPLACE.
    Automatically migrates existing tables to add temp, humidity, pop, rainfall, pm25, and uvi columns.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                temp REAL DEFAULT 25.0,
                minT REAL NOT NULL,
                maxT REAL NOT NULL,
                weather TEXT DEFAULT '',
                humidity REAL DEFAULT 70.0,
                pop REAL DEFAULT 0.0,
                rainfall REAL DEFAULT 0.0,
                pm25 REAL DEFAULT 15.0,
                uvi REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
            );
        """)
        
        # Schema migration check: Add new columns if table existed without them
        cursor.execute("PRAGMA table_info(TemperatureForecasts);")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        
        # 【修改點 1】：檢查並新增 temp 欄位
        if "temp" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN temp REAL DEFAULT 25.0;")
            
        if "humidity" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN humidity REAL DEFAULT 70.0;")
        if "pop" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN pop REAL DEFAULT 0.0;")
        if "rainfall" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN rainfall REAL DEFAULT 0.0;")
        if "pm25" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN pm25 REAL DEFAULT 15.0;")
        if "uvi" not in existing_cols:
            cursor.execute("ALTER TABLE TemperatureForecasts ADD COLUMN uvi REAL DEFAULT 0.0;")

        conn.commit()

def save_forecasts(records: List[Dict[str, Any]], db_path: str = DB_FILE) -> int:
    """
    Step 8: Insert or replace forecast records into TemperatureForecasts table.
    Returns the number of records inserted/updated.
    """
    init_db(db_path)
    clean_records = []
    for r in records:
        min_t = float(r.get("minT", 20.0))
        max_t = float(r.get("maxT", 28.0))
        
        # 【修改點 2】：若記錄內沒有 temp，預設取 minT 與 maxT 的平均
        default_temp = round((min_t + max_t) / 2.0, 1)
        
        clean_records.append({
            "regionName": r.get("regionName", ""),
            "dataDate": r.get("dataDate", ""),
            "temp": float(r.get("temp", default_temp)),  # 新增 temp
            "minT": min_t,
            "maxT": max_t,
            "weather": str(r.get("weather", "")),
            "humidity": float(r.get("humidity", 70.0)),
            "pop": float(r.get("pop", 0.0)),
            "rainfall": float(r.get("rainfall", 0.0)),
            "pm25": float(r.get("pm25", 15.0)),
            "uvi": float(r.get("uvi", 0.0))
        })

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # 【修改點 3】：修改 INSERT 與 ON CONFLICT 子句加入 temp
        cursor.executemany("""
            INSERT INTO TemperatureForecasts (regionName, dataDate, temp, minT, maxT, weather, humidity, pop, rainfall, pm25, uvi)
            VALUES (:regionName, :dataDate, :temp, :minT, :maxT, :weather, :humidity, :pop, :rainfall, :pm25, :uvi)
            ON CONFLICT(regionName, dataDate) DO UPDATE SET
                temp = excluded.temp,
                minT = excluded.minT,
                maxT = excluded.maxT,
                weather = excluded.weather,
                humidity = excluded.humidity,
                pop = excluded.pop,
                rainfall = excluded.rainfall,
                pm25 = excluded.pm25,
                uvi = excluded.uvi,
                created_at = CURRENT_TIMESTAMP;
        """, clean_records)
        conn.commit()
        return len(clean_records)

def query_distinct_regions(db_path: str = DB_FILE) -> List[str]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY id;")
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def query_cities_only(db_path: str = DB_FILE) -> List[str]:
    all_locations = query_distinct_regions(db_path)
    return [loc for loc in all_locations if loc.endswith(("市", "縣"))]

def query_regional_divisions_only(db_path: str = DB_FILE) -> List[str]:
    all_locations = query_distinct_regions(db_path)
    return [loc for loc in all_locations if loc.endswith("地區")]

def query_forecast_by_region(region_name: str, db_path: str = DB_FILE) -> pd.DataFrame:
    init_db(db_path)
    conn = get_connection(db_path)
    query = """
        SELECT dataDate, temp, minT, maxT, weather, humidity, pop, rainfall, pm25, uvi 
        FROM TemperatureForecasts 
        WHERE regionName = ? 
        ORDER BY dataDate ASC
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df

def query_forecast_by_date(date_str: str, db_path: str = DB_FILE) -> pd.DataFrame:
    """
    Step 18: Query all regions forecast for a specific date.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    # 【修改點 4】：SELECT 查詢語法中加入 temp 欄位
    query = """
        SELECT regionName, dataDate, temp, minT, maxT, weather, humidity, pop, rainfall, pm25, uvi 
        FROM TemperatureForecasts 
        WHERE dataDate = ?
        ORDER BY regionName ASC
    """
    df = pd.read_sql_query(query, conn, params=(date_str,))
    conn.close()
    return df

def query_all_forecasts(db_path: str = DB_FILE) -> pd.DataFrame:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM TemperatureForecasts ORDER BY regionName, dataDate ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_available_dates(db_path: str = DB_FILE) -> List[str]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dataDate FROM TemperatureForecasts ORDER BY dataDate ASC;")
        rows = cursor.fetchall()
        return [row[0] for row in rows]