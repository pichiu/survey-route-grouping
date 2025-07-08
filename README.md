# survey-route-grouping

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
│       │   └── queries.py          # SQL 查詢
│       ├── models/
│       │   ├── __init__.py
│       │   ├── address.py          # 地址資料模型
│       │   └── group.py            # 分組結果模型
│       ├── algorithms/
│       │   ├── __init__.py
│       │   ├── address_classifier.py  # 地址類型分類
│       │   ├── clustering.py       # 聚類演算法
│       │   ├── route_optimizer.py  # 路線優化
│       │   └── grouping_engine.py  # 主要分組引擎
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── geo_utils.py        # 地理計算工具
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

### 1. 專案初始化
```bash
# 建立專案
uv init survey-route-grouping
cd survey-route-grouping

# 複製 pyproject.toml 內容
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

### 3. 測試連接
```bash
# 測試資料庫連接
uv run survey-grouping test-connection
```

### 4. 開始使用
```bash
# 基本分組
uv run survey-grouping create-groups 新營區 三仙里

# 進階功能
uv run survey-grouping analyze-density 新營區
uv run survey-grouping batch-process 新營區
```

### 基本命令
```bash
# 安裝依賴
uv sync

# 基本分組 (35人一組)
uv run survey-grouping create-groups 新營區 三仙里

# 自訂組別大小
uv run survey-grouping create-groups 新營區 三仙里 --target-size 40

# 輸出 Excel 檔案
uv run survey-grouping create-groups 新營區 三仙里 --output-format excel --output-file 三仙里普查分組.xlsx
```

### 程式化使用
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

## 授權條款

### 程式碼授權
本專案程式碼採用 MIT License。詳見 [LICENSE](LICENSE) 檔案。

### 資料授權
資料來源：臺南市政府 113年 臺南市門牌坐標資料

此開放資料依政府資料開放授權條款 (Open Government Data License) 進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。

授權條款：https://data.gov.tw/license
