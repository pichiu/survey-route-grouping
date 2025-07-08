# Survey Route Grouping - 普查路線分組系統

基於 Supabase + PostGIS 的智慧型普查路線分組系統，支援 WGS84 座標系統和空間地理分析。

## 🎯 專案特色

- **空間地理分析**：基於 PostGIS 的精確地理距離計算和空間索引
- **智慧分組演算法**：結合地址分類和地理聚類的多層次分組策略
- **WGS84 座標支援**：完整支援國際標準座標系統
- **彈性目標人數**：可自訂每組目標人數（預設 35 人）
- **路線優化**：自動產生最佳訪問順序
- **多格式輸出**：支援 CSV、JSON、Excel 等格式

## 🏗️ 資料庫架構

### Supabase + PostGIS 設置

本專案使用 Supabase 作為資料庫，並啟用 PostGIS 擴展進行空間地理分析。

#### 1. 建立 Supabase 專案
1. 前往 [Supabase](https://supabase.com) 建立新專案
2. 在 SQL Editor 中執行以下 SQL 來啟用 PostGIS：

```sql
-- 啟用 PostGIS 擴展
CREATE EXTENSION IF NOT EXISTS postgis;
```

#### 2. 資料表結構

```sql
-- 建立地址資料表
CREATE TABLE addresses (
    id BIGSERIAL PRIMARY KEY,
    district VARCHAR(10) NOT NULL,
    village VARCHAR(20) NOT NULL,
    neighborhood INTEGER NOT NULL,
    street VARCHAR(100),
    area VARCHAR(50),
    lane VARCHAR(20),
    alley VARCHAR(20),
    number VARCHAR(50),
    x_coord DECIMAL(10, 6),
    y_coord DECIMAL(10, 6),
    full_address TEXT,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 建立統計快取表
CREATE TABLE address_stats (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    district VARCHAR(10),
    village VARCHAR(20),
    neighborhood INTEGER,
    address_count INTEGER NOT NULL DEFAULT 0,
    village_count INTEGER DEFAULT 0,
    neighborhood_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(level, district, village, neighborhood)
);

-- 建立索引
CREATE INDEX idx_addresses_district ON addresses(district);
CREATE INDEX idx_addresses_village ON addresses(district, village);
CREATE INDEX idx_addresses_neighborhood ON addresses(district, village, neighborhood);
CREATE INDEX idx_addresses_coords ON addresses(x_coord, y_coord);
CREATE INDEX idx_addresses_geom ON addresses USING GIST(geom);
CREATE INDEX idx_addresses_full_address ON addresses(full_address);

-- 建立觸發器自動更新 full_address 和 geom
CREATE OR REPLACE FUNCTION update_address_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- 更新完整地址
    NEW.full_address := CONCAT(
        COALESCE(NEW.street, ''),
        COALESCE(NEW.area, ''),
        COALESCE(NEW.lane, ''),
        COALESCE(NEW.alley, ''),
        COALESCE(NEW.number, '')
    );

    -- 更新地理座標
    IF NEW.x_coord IS NOT NULL AND NEW.y_coord IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.x_coord, NEW.y_coord), 4326);
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_address_fields
    BEFORE INSERT OR UPDATE ON addresses
    FOR EACH ROW EXECUTE FUNCTION update_address_fields();

-- 啟用 Row Level Security (RLS)
ALTER TABLE addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE address_stats ENABLE ROW LEVEL SECURITY;

-- 建立公開讀取政策
CREATE POLICY "addresses_select_policy" ON addresses
FOR SELECT USING (true);

CREATE POLICY "address_stats_select_policy" ON address_stats
FOR SELECT USING (true);
```

#### 3. 座標系統說明
- **座標系統**：WGS84 (EPSG:4326)
- **座標格式**：經度 (x_coord), 緯度 (y_coord)
- **空間資料**：PostGIS GEOMETRY 類型，支援空間索引和查詢
- **距離計算**：使用 PostGIS 的地理函數進行精確計算

## 📁 專案結構
```
survey_route_grouping/
├── pyproject.toml
├── README.md
├── .env.example
├── .env                    # 不要提交到 Git
├── .gitignore
├── src/
│   └── survey_grouping/
│       ├── __init__.py
│       ├── main.py                 # CLI 入口點
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py         # 配置設定
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py       # Supabase 連接
│       │   └── queries.py          # SQL 查詢（含空間查詢）
│       ├── models/
│       │   ├── __init__.py
│       │   ├── address.py          # 地址資料模型
│       │   ├── address_stats.py    # 統計資料模型
│       │   └── group.py            # 分組結果模型
│       ├── algorithms/
│       │   ├── __init__.py
│       │   ├── address_classifier.py  # 地址類型分類
│       │   ├── clustering.py       # 空間聚類演算法
│       │   ├── route_optimizer.py  # 路線優化
│       │   └── grouping_engine.py  # 主要分組引擎
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── geo_utils.py        # 地理計算工具（PostGIS）
│       │   └── validators.py       # 資料驗證
│       └── exporters/
│           ├── __init__.py
│           ├── csv_exporter.py     # CSV 輸出
│           ├── json_exporter.py    # JSON 輸出
│           └── excel_exporter.py   # Excel 輸出
├── tests/
│   ├── __init__.py
│   ├── test_clustering.py
│   ├── test_database.py
│   └── fixtures/
│       └── sample_data.json
└── examples/
    ├── basic_usage.py
    └── advanced_grouping.py
```

## 🚀 快速開始

### 1. 專案初始化
```bash
# 建立專案
uv init survey-route-grouping
cd survey-route-grouping

# 安裝依賴
uv sync
```

### 2. 環境設置
```bash
# 方法一：互動式設置（推薦）
uv run survey-grouping setup-env

# 方法二：手動建立 .env 檔案
cp .env.example .env
# 編輯 .env 填入您的 Supabase 資訊
```

#### .env 檔案範例
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
DEFAULT_GROUP_SIZE=35
```

### 3. 資料庫設置
```bash
# 測試資料庫連接
uv run survey-grouping test-connection

# 檢查 PostGIS 功能
uv run survey-grouping test-postgis
```

### 4. 開始使用
```bash
# 基本分組（35人一組）
uv run survey-grouping create-groups 新營區 三仙里

# 自訂組別大小
uv run survey-grouping create-groups 新營區 三仙里 --target-size 40

# 輸出 Excel 檔案
uv run survey-grouping create-groups 新營區 三仙里 --output-format excel --output-file 三仙里普查分組.xlsx

# 分析地址密度
uv run survey-grouping analyze-density 新營區

# 批次處理整個區
uv run survey-grouping batch-process 新營區
```

## 💻 程式化使用

### 基本使用範例
```python
from survey_grouping.algorithms.grouping_engine import GroupingEngine
from survey_grouping.database.connection import get_supabase_client
from survey_grouping.database.queries import AddressQueries

# 建立分組
supabase = get_supabase_client()
queries = AddressQueries(supabase)
addresses = await queries.get_addresses_by_village("新營區", "三仙里")

engine = GroupingEngine(target_size=35)
groups = engine.create_groups(addresses, "新營區", "三仙里")

# 取得結果
for group in groups:
    print(f"{group.group_id}: {group.size} 個門牌")
    for addr in group.addresses:
        print(f"  - {addr.full_address}")
```

### 進階空間查詢範例
```python
from survey_grouping.database.queries import AddressQueries

# 使用空間查詢找出指定範圍內的地址
queries = AddressQueries(supabase)

# 找出距離某點 500 公尺內的地址
nearby_addresses = await queries.get_addresses_within_distance(
    center_x=120.123456, 
    center_y=23.123456, 
    distance_meters=500
)

# 取得村里的地理中心點
center = await queries.get_village_center("新營區", "三仙里")
```

## 🔧 核心功能

### 1. 智慧分組演算法
- **地址分類**：自動識別街道型、地區型、鄰別型地址
- **空間聚類**：基於 PostGIS 的地理距離聚類
- **負載平衡**：確保各組人數接近目標值
- **路線優化**：產生最佳訪問順序

### 2. 空間地理分析
- **精確距離計算**：使用 WGS84 座標系統
- **空間索引查詢**：利用 PostGIS GIST 索引
- **地理統計**：地址密度分析和熱點識別
- **空間關係**：鄰近性分析和區域劃分

### 3. 效能優化
- **統計快取**：address_stats 表提供快速統計
- **空間索引**：GIST 索引加速空間查詢
- **批次處理**：支援大量資料的高效處理
- **記憶體管理**：串流處理避免記憶體溢出

## 📊 輸出格式

### 路線分組結果
```json
{
  "group_id": "新營區三仙里-01",
  "size": 35,
  "estimated_distance": 1.2,
  "estimated_time": 45,
  "addresses": [
    {
      "id": 1,
      "full_address": "新營區三仙里中山路123號",
      "coordinates": [120.123456, 23.123456]
    }
  ],
  "route_order": [1, 5, 3, 2, 4]
}
```

### 統計報告
```json
{
  "district": "新營區",
  "village": "三仙里",
  "total_addresses": 350,
  "total_groups": 10,
  "avg_group_size": 35,
  "coverage_area": 2.5,
  "estimated_total_time": 450
}
```

## 🧪 測試

```bash
# 執行所有測試
uv run pytest

# 測試特定模組
uv run pytest tests/test_clustering.py

# 測試資料庫連接
uv run pytest tests/test_database.py -v
```

## 📈 效能考量

### 資料庫優化
- 使用空間索引加速地理查詢
- 統計表快取常用查詢結果
- 批次查詢減少資料庫往返

### 演算法優化
- 多層次分組減少計算複雜度
- 空間分割避免全域計算
- 記憶體友善的串流處理

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權條款

### 程式碼授權
本專案程式碼採用 MIT License。詳見 [LICENSE](LICENSE) 檔案。

### 資料授權
資料來源：臺南市政府 113年 臺南市門牌坐標資料

此開放資料依政府資料開放授權條款 (Open Government Data License) 進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。

授權條款：https://data.gov.tw/license

## 🔗 相關連結

- [Supabase 文件](https://supabase.com/docs)
- [PostGIS 文件](https://postgis.net/documentation/)
- [WGS84 座標系統](https://epsg.io/4326)
- [臺南市開放資料平台](https://data.tainan.gov.tw/)
