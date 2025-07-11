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
│       ├── visualizers/
│       │   ├── __init__.py
│       │   ├── map_visualizer.py   # 主要地圖視覺化類別
│       │   ├── folium_renderer.py  # Folium 渲染器
│       │   └── color_schemes.py    # 顏色配置
│       ├── importers/              # 🆕 CSV 導入功能
│       │   ├── __init__.py
│       │   └── csv_importer.py     # CSV 分組結果導入器
│       └── exporters/
│           ├── __init__.py
│           ├── csv_exporter.py     # CSV 輸出
│           ├── json_exporter.py    # JSON 輸出
│           ├── excel_exporter.py   # Excel 輸出
│           └── map_exporter.py     # 地圖匯出功能
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
# 基本分組（從資料庫，35人一組）
uv run survey-grouping create-groups 新營區 三仙里

# 從 CSV 檔案進行分組 🆕
uv run survey-grouping create-groups --input-csv data/addresses.csv --output-file result.csv

# 自訂組別大小
uv run survey-grouping create-groups 新營區 三仙里 --target-size 40

# 輸出 Excel 檔案
uv run survey-grouping create-groups 新營區 三仙里 --output-format excel --output-file 三仙里普查分組.xlsx

# 從 CSV 輸入並輸出不同格式 🆕
uv run survey-grouping create-groups --input-csv addresses.csv --output-format excel --output-file groups.xlsx

# 生成互動式地圖視覺化
uv run survey-grouping visualize 新營區 三仙里

# 從已存在的 CSV 檔案生成地圖（支援手動微調的分組）
uv run survey-grouping visualize-from-csv output/分組結果.csv

# 分析地址密度
uv run survey-grouping analyze-density 新營區

# 批次處理整個區
uv run survey-grouping batch-process 新營區

# 查詢特定地址的座標 🆕
uv run survey-grouping query-coordinates 七股區 頂山里 頂山13號

# 使用 VillageProcessor 處理 Excel 數據 🆕
uv run python src/survey_grouping/processors/village_processor.py --district 七股區 --village 頂山里 --excel-path data/頂山里200戶.xlsx
```

#### CSV 輸入格式 🆕
支援從 CSV 檔案直接讀取地址資料進行分組，無需建立資料庫：

**必要欄位**：
- `完整地址`：完整門牌地址
- `區域`：行政區名稱（如：七股區）
- `村里`：村里名稱（如：頂山里）
- `鄰別`：鄰別編號（整數）
- `經度`：WGS84 經度座標
- `緯度`：WGS84 緯度座標

**CSV 範例**：
```csv
完整地址,區域,村里,鄰別,經度,緯度
頂山10號,七股區,頂山里,1,120.111765,23.180684
頂山13號,七股區,頂山里,1,120.112034,23.180486
頂山14號,七股區,頂山里,1,120.111924,23.180515
```

**使用場景**：
- 🎯 **快速原型**：無需設置資料庫即可測試分組功能
- 📊 **資料探索**：對現有地址資料進行分組分析
- 🔄 **工作流整合**：結合其他系統的 CSV 輸出進行處理
- 📱 **小型專案**：適合地址數量較少的場景

#### VillageProcessor Excel 處理 🆕
支援將 Excel 村里數據轉換為標準化 CSV 格式並匹配座標：

**支援的 Excel 格式**：
1. **多工作表格式**：每個工作表代表一個鄰別
2. **單工作表格式**：所有資料在一個工作表，包含鄰別欄位
3. **名冊格式**：包含完整地址的名冊格式

**核心功能**：
- ✅ **地址標準化**：自動轉換 74-1號 → 74號之1
- ✅ **全形轉半形**：支援全形數字轉換（１２３ → 123）
- ✅ **精確匹配**：禁用模糊匹配避免錯誤配對
- ✅ **跨區域過濾**：自動識別並分離跨區域地址
- ✅ **跨村里處理**：可選支援同區其他村里地址的座標匹配 🆕
- ✅ **未匹配報告**：生成詳細的未匹配地址清單

**使用範例**：
```bash
# 處理 Excel 數據（自動格式偵測）
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 七股里 \
  --excel-path data/七股里.xlsx

# 自訂輸出路徑
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 頂山里 \
  --excel-path data/頂山里200戶.xlsx \
  --output-path output/頂山里處理結果.csv

# 去除重複地址
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 頂山里 \
  --excel-path data/頂山里200戶.xlsx \
  --remove-duplicates

# 🆕 包含跨村里地址處理（同區其他村里地址也會匹配座標）
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 七股里 \
  --excel-path data/七股里.xlsx \
  --include-cross-village
```

**輸出檔案**：
- `{區域}{村里}分組結果.csv`：主要結果檔案（目標村里地址）
- `{區域}{村里}分組結果_未匹配地址.csv`：未匹配地址報告
- `{區域}{村里}分組結果_無效地址.csv`：跨區域地址報告（名冊格式）
- `{區域}{村里}分組結果_跨村里地址.csv`：跨村里地址報告（使用 --include-cross-village 時）🆕

#### 跨村里地址處理功能 🆕

VillageProcessor 支援兩種處理模式：

**📍 單村里模式（預設）**：
- 只處理目標村里的地址
- 同區其他村里地址會被歸類為「無效地址」
- 適合嚴格的村里範圍普查

**🌐 包含跨村里模式（`--include-cross-village`）**：
- 處理目標村里地址 + 同區其他村里地址
- 跨村里地址會匹配對應村里的座標資料
- 生成獨立的跨村里地址報告
- 適合需要處理混合地址的場景

**實際應用場景**：
```bash
# 場景1：七股里名冊包含塩埕里地址
# 單村里模式：塩埕里地址 → 無效地址報告
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 七股里 \
  --excel-path data/七股里.xlsx

# 跨村里模式：塩埕里地址 → 跨村里地址報告（含座標）
uv run python src/survey_grouping/processors/village_processor.py \
  --district 七股區 --village 七股里 \
  --excel-path data/七股里.xlsx \
  --include-cross-village
```

**處理邏輯差異**：
- **同區同村里**：`臺南市七股區七股里13鄰七股123號` → 主要結果檔案
- **同區跨村里**：`臺南市七股區塩埕里6鄰鹽埕237號` → 跨村里報告（有 --include-cross-village）或無效地址報告（預設）
- **跨區地址**：`臺南市安南區七股116號` → 無效地址報告（兩種模式皆同）

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

### 3. 地址查詢功能 🆕
- **精確查詢**：根據完整地址查找座標資訊
- **模糊搜尋**：支援部分地址匹配和相似地址搜尋
- **批量查詢**：支援鄰別範圍內的地址查詢
- **座標驗證**：即時檢查座標資料的準確性

### 4. VillageProcessor 資料處理器 🆕
- **多格式支援**：自動偵測並支援多工作表、單工作表、名冊格式 Excel 檔案
- **地址標準化**：智慧轉換地址格式（如 74-1號 → 74號之1）
- **精確匹配**：禁用模糊匹配避免錯誤配對，提供更準確的座標匹配
- **跨區域過濾**：自動識別並過濾跨區域地址，生成無效地址報告
- **全形數字轉換**：支援全形數字自動轉半形（１２３ → 123）
- **未匹配報告**：生成詳細的未匹配地址報告供手動處理

### 5. 效能優化
- **統計快取**：address_stats 表提供快速統計
- **空間索引**：GIST 索引加速空間查詢
- **批次處理**：支援大量資料的高效處理
- **記憶體管理**：串流處理避免記憶體溢出

## 🗺️ 資料視覺化

### 互動式地圖視覺化
基於 Folium + OpenStreetMap 的互動式地圖，提供直觀的路線分組視覺化。

#### 功能特色
- **總覽地圖**：所有分組在同一張地圖上，不同顏色區分
- **個別分組地圖**：每組獨立地圖，顯示詳細路線和訪問順序
- **互動功能**：點擊標記查看地址詳情、距離和時間資訊
- **路線視覺化**：顯示最佳訪問路徑和順序編號
- **離線使用**：生成 HTML 檔案，可離線開啟使用

#### 視覺化命令
```bash
# 生成完整視覺化地圖（總覽 + 個別分組）
uv run survey-grouping visualize 七股區 西寮里

# 指定輸出目錄
uv run survey-grouping visualize 七股區 西寮里 --output-dir maps/

# 只生成總覽圖
uv run survey-grouping visualize 七股區 西寮里 --overview-only

# 只生成個別分組圖
uv run survey-grouping visualize 七股區 西寮里 --groups-only

# 自訂目標分組大小
uv run survey-grouping visualize 七股區 西寮里 --target-size 30

# 從 CSV 檔案生成視覺化地圖（支援微調後的分組）
uv run survey-grouping visualize-from-csv output/七股區西寮里分組結果.csv --output-dir maps/
```

#### 輸出檔案結構
```
maps/
├── 七股區西寮里_總覽.html          # 所有分組總覽
├── 七股區西寮里_第1組.html         # 第1組詳細路線
├── 七股區西寮里_第2組.html         # 第2組詳細路線
└── 七股區西寮里_第3組.html         # 第3組詳細路線
```

#### 地圖功能說明
- **顏色編碼**：每個分組使用不同顏色的標記
- **訪問順序**：標記上顯示訪問順序編號（1, 2, 3...）
- **路線連線**：顯示最佳化的訪問路徑
- **資訊彈窗**：點擊標記顯示地址、座標、分組資訊
- **圖層控制**：可切換顯示/隱藏不同分組
- **統計面板**：顯示分組統計資訊（距離、時間、地址數量）

### CSV 導入視覺化功能 🆕

支援從既有的 CSV 分組結果檔案直接生成視覺化地圖，方便處理手動微調後的分組資料。

#### 支援的 CSV 格式
**必要欄位**：
- `分組編號`：如「七股區西寮里-01」
- `完整地址`：完整門牌地址
- `區域`、`村里`、`鄰別`：行政區劃資訊
- `經度`、`緯度`：WGS84 座標

**Optional 欄位**（可省略）：
- `分組大小`、`目標大小`：分組統計資訊
- `預估距離(公尺)`、`預估時間(分鐘)`：路線資訊
- `地址ID`、`訪問順序`：路線優化相關

#### 使用範例
```bash
# 完整格式 CSV（包含路線順序）
uv run survey-grouping visualize-from-csv output/完整分組結果.csv

# 簡化格式 CSV（僅基本資訊，不顯示路線）
uv run survey-grouping visualize-from-csv output/簡化分組結果.csv

# 指定輸出目錄
uv run survey-grouping visualize-from-csv data.csv --output-dir custom_maps/
```

#### 智慧處理邏輯
- ✅ **有訪問順序**：顯示路線連線、順序編號、方向箭頭
- ✅ **無訪問順序**：僅顯示分組標記點，不計算路線
- ✅ **BOM 字元處理**：自動處理 UTF-8 BOM 編碼問題
- ✅ **格式驗證**：自動檢查 CSV 格式並提供錯誤提示

#### 使用場景
- **志工培訓**：視覺化展示分組區域和路線
- **現場導航**：志工可用手機開啟 HTML 檔案進行導航
- **進度追蹤**：管理者可視化監控各組進度
- **路線優化**：直觀檢視和調整分組策略
- **微調支援**：匯出 CSV → 手動調整 → 重新視覺化

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
