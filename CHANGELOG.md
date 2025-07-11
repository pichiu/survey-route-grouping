# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### 🛠️ RouteProcessor 路線分組處理器 🆕
- **新增 RouteProcessor 類別** (`src/survey_grouping/processors/route_processor.py`)：
  - 專門處理路線分組 Excel 檔案的資料處理器
  - 支援多工作表路線分組格式，每個工作表代表一條路線
  - 動態路線命名：自動生成如 篤加01、西寮02 等路線名稱
  - 跨村里地址檢測：智慧識別並過濾不同村里的地址
  - 混合地址格式支援：同時處理完整地址和簡單地址
  - 資料庫鄰別查詢：自動查詢缺少鄰別資訊的地址
  - 字符一致性處理：處理塩埕/鹽埕等字符變異問題
  - 全面地址保留：包含所有有效地址（即使無座標匹配）

#### 🔧 RouteProcessor 核心功能詳細
- **Excel 格式支援**：
  - 第一個工作表「核定名冊」自動跳過
  - 其他工作表代表路線（如：篤加1、篤加2、西寮1、西寮2）
  - 支援動態欄位數量（4欄或6欄格式）
- **地址處理邏輯**：
  - `_is_target_village_address()`：目標村里完整地址檢測
  - `_is_simple_village_address()`：簡單村里地址檢測（含跨村里衝突處理）
  - `_is_different_village_address()`：不同村里地址檢測
  - `_process_target_village_address()`：目標村里地址處理
  - `_process_simple_village_address()`：簡單村里地址處理
- **關鍵修復**：
  - 修復七股里/七股區同名前綴導致的地址誤判問題
  - 改進正則表達式：使用 `[\u4e00-\u9fff]+里` 匹配中文村里名稱
  - 解決 `臺南市七股區塩埕里6鄰鹽埕237號之3` 被誤認為七股里地址的問題
- **輸出檔案**：
  - `{區域}{村里}動線處理結果.csv`：所有有效地址（含座標和未匹配）
  - `{區域}{村里}動線處理結果_未匹配地址.csv`：未找到座標的地址
  - `{區域}{村里}動線處理結果_無效地址.csv`：跨村里或無效地址

#### 🧪 RouteProcessor 實際應用成果
- **成功處理8個村里**：中寮里、玉成里、永吉里、後港里、竹橋里、十份里、七股里、塩埕里
- **整體匹配率**：93.7% (313/334 筆地址)
- **跨村里地址檢測**：成功識別並過濾2筆跨村里地址
- **字符一致性處理**：正確處理塩埕里（塩）與鹽埕里（鹽）的字符差異

#### 🛠️ VillageProcessor 資料處理器
- **新增 VillageProcessor 類別** (`src/survey_grouping/processors/village_processor.py`)：
  - 通用村里數據處理器，支援 Excel 數據轉換為 CSV 格式並匹配座標
  - 地址標準化和 Supabase 座標匹配功能
  - 完整的工作流程：Excel → 標準化地址 → 座標查詢 → CSV 輸出
  - 未匹配地址報告生成，支援後續手動處理

#### 🔍 地址座標查詢功能 🆕
- **新增 `query-coordinates` 命令**：支援查詢特定地址的經緯度座標
- **多層查詢策略**：
  - 精確匹配：優先使用完整地址進行精確查詢
  - 模糊搜尋：當精確匹配失敗時，自動進行模糊匹配搜尋
  - 鄰別查詢：可選擇性指定鄰別，提供額外的上下文資訊
- **格式化輸出**：
  - 單一結果：顯示地址、座標、鄰別、資料庫ID
  - 多重結果：以表格形式顯示搜尋結果，包含ID、地址、鄰別、經緯度
  - 限制顯示：搜尋結果超過10筆時僅顯示前10筆，並提示總數
- **命令使用範例**：
  ```bash
  # 基本座標查詢
  uv run survey-grouping query-coordinates 七股區 頂山里 頂山13號
  
  # 指定鄰別進行查詢
  uv run survey-grouping query-coordinates 七股區 頂山里 頂山13號 --neighborhood 1
  ```
- **資料庫查詢方法擴充**：
  - `get_address_by_full_address()` 方法：精確地址查詢
  - `search_addresses_by_pattern()` 方法：模糊地址搜尋
  - 支援完整的異步查詢流程

#### 🆕 CSV 輸入分組功能
- **新增 `--input-csv` 參數**：`create-groups` 命令現在支援從 CSV 檔案讀取地址資料進行分組
- **彈性輸入模式**：
  - 資料庫模式：使用 `district` 和 `village` 參數從 Supabase 讀取
  - CSV 模式：使用 `--input-csv` 參數從本地 CSV 檔案讀取
- **CSV 格式支援**：
  - 必要欄位：完整地址、區域、村里、鄰別、經度、緯度
  - 自動從 CSV 資料推斷區域和村里資訊
  - 支援 UTF-8 和 UTF-8-BOM 編碼格式
- **無資料庫依賴**：CSV 模式下無需連接 Supabase 資料庫即可進行分組

#### 🆕 CSV 導入視覺化功能
- **新增 `visualize-from-csv` 命令**：支援從既有的 CSV 分組結果直接生成視覺化地圖
- **彈性 CSV 格式支援**：
  - 必要欄位：分組編號、完整地址、區域、村里、鄰別、經度、緯度
  - Optional 欄位：分組大小、目標大小、預估距離、預估時間、地址ID、訪問順序
- **智慧路線處理**：
  - 有訪問順序時：顯示路線連線、順序編號、方向箭頭
  - 無訪問順序時：僅顯示分組標記點，不進行路線計算
- **格式驗證與錯誤處理**：
  - 自動檢查 CSV 格式完整性
  - 支援 UTF-8 BOM 編碼處理
  - 提供詳細的錯誤訊息和修正建議

#### 🔧 新增模組與類別
- **CSVImporter 類別** (`src/survey_grouping/importers/csv_importer.py`)：
  - `CSVGroupRow` 模型：CSV 資料列的 Pydantic 模型
  - `read_csv_file()` 方法：讀取和解析 CSV 檔案
  - `validate_csv_format()` 方法：CSV 格式驗證（支援地址資料和分組結果兩種模式）
  - `import_from_csv()` 方法：完整的 CSV 導入流程
  - `import_addresses_from_csv()` 方法：從 CSV 讀取地址資料轉換為 Address 物件列表 🆕
  - `convert_to_route_groups()` 方法：轉換為 RouteGroup 物件

#### 🏗️ VillageProcessor 多格式支援擴充 ✨
- **新增名冊格式支援** (`src/survey_grouping/processors/village_processor.py`)：
  - 自動偵測並支援三種 Excel 格式：多工作表、單工作表、名冊格式
  - 新增 `_read_roster_format()` 方法：處理包含完整地址的名冊格式
  - 新增 `convert_fullwidth_to_halfwidth()` 函數：全形數字自動轉半形（１２３ → 123）
  - 新增 `extract_neighborhood_from_address()` 函數：從完整地址提取鄰別資訊
  - 新增 `export_invalid_addresses()` 方法：導出跨區域地址報告

#### 🔧 關鍵地址標準化修復 🚨
- **修復 dash-to-zhi 轉換漏洞** (`_standardize_roster_address()` 方法)：
  - **修復前**：名冊格式中的 "74-1號" 未被標準化，造成匹配失敗
  - **修復後**：正確轉換 "74-1號" → "74號之1"，匹配率從 90.6% 提升至 96.9%
  - 在 `_standardize_roster_address()` 中添加對 `standardize_village_address()` 的調用
  - 確保 dash-to-zhi 轉換邏輯在所有格式中都能正確執行

#### 🔍 跨區域地址處理強化
- **智慧地址過濾** (`_read_roster_format()` 方法)：
  - 自動識別非目標區域和村里的地址
  - 將跨區域地址記錄到 `invalid_addresses` 列表
  - 生成專門的無效地址報告，便於後續手動處理
  - 提供詳細的問題原因說明（如："非七股區七股里地址"）

#### 🌐 VillageProcessor 跨村里處理功能 🆕
- **新增 `--include-cross-village` 參數**：
  - 支援同區其他村里地址的座標匹配和處理
  - 維持向後相容性：預設為單村里嚴格模式
  - 新增 `include_cross_village` 初始化參數到 VillageProcessor 類別
- **雙模式處理架構**：
  - **單村里模式（預設）**：只處理目標村里地址，跨村里地址歸類為無效地址
  - **跨村里模式**：處理目標村里 + 同區其他村里地址，各自匹配對應座標
- **新增方法擴充**：
  - `_standardize_cross_village_address()` 方法：跨村里地址標準化邏輯
  - `_extract_village_name()` 方法：從完整地址中提取村里名稱
  - `export_cross_village_addresses()` 方法：導出跨村里地址 CSV 報告
  - `query_address_coordinates()` 新增 `target_village` 參數：支援指定村里查詢
- **處理邏輯改進**：
  - 跨村里地址自動提取村里名稱用於精確座標查詢
  - 修改 `process_data()` 回傳值：`(processed_data, unmatched, cross_village)` 
  - 在 `_read_roster_format()` 中分離跨村里地址到獨立資料結構
- **輸出檔案擴充**：
  - 新增 `{區域}{村里}分組結果_跨村里地址.csv` 報告檔案
  - 跨村里地址包含：序號、姓名、完整地址、區域、村里、鄰別、經緯度
  - CLI 自動生成跨村里地址報告（當有資料且啟用跨村里模式時）
- **實際應用價值**：
  - 解決名冊資料包含混合村里地址的實際需求
  - 提供彈性的處理模式滿足不同普查場景
  - 保持資料完整性：所有地址都能得到適當處理和分類

### Changed

#### 🔒 VillageProcessor 精確匹配改進
- **禁用模糊匹配** (`src/survey_grouping/processors/village_processor.py`)：
  - 移除 `query_address_coordinates()` 方法中的模糊匹配邏輯
  - 僅使用精確匹配避免錯誤的地址配對（如 頂山2號之3 誤配到 頂山23號）
  - 找不到匹配的地址直接返回 None，不進行模糊搜尋
  - 所有地址（包含未匹配）都會加入最終 CSV 輸出，座標留空為 None
  - 新增完整的測試覆蓋，包含精確匹配驗證和模糊匹配禁用測試

#### 🎨 視覺化邏輯優化
- **FoliumRenderer 改進** (`src/survey_grouping/visualizers/folium_renderer.py`)：
  - `_add_route_line()` 方法：只在有路線順序時繪製連線
  - `_add_detailed_route()` 方法：只在有路線順序時顯示詳細路線和箭頭
  - `_add_ordered_markers()` 方法：智慧切換有序/無序標記顯示
  - 新增 `_add_group_markers_to_map()` 方法：處理無順序的一般標記

#### 📋 命令列介面擴充
- **main.py 更新**：
  - 新增 `visualize-from-csv` 命令及其參數選項
  - 修改 `create-groups` 命令支援 `--input-csv` 參數 🆕
  - 參數調整：`district` 和 `village` 改為可選參數，支援 CSV 輸入模式
  - 整合 CSVImporter 到主要 CLI 介面
  - 改進錯誤處理和使用者提示訊息

#### 🧪 全面測試覆蓋 ✅
- **新增 TestUtilityFunctions 測試類別** (`tests/test_village_processor.py`)：
  - `test_convert_fullwidth_to_halfwidth()`：測試全形數字轉換功能
  - `test_extract_neighborhood_from_address()`：測試鄰別提取功能
- **新增 TestRosterFormatProcessing 測試類別** (`tests/test_village_processor.py`)：
  - `test_roster_format_detection()`：測試名冊格式自動偵測
  - `test_roster_format_with_fullwidth_numbers()`：測試全形數字處理
  - `test_roster_format_cross_district_filtering()`：測試跨區域地址過濾
  - `test_standardize_roster_address_dash_to_zhi_conversion()`：**關鍵測試** - 驗證 dash-to-zhi 轉換修復
  - `test_export_invalid_addresses_report()`：測試無效地址報告生成
  - `test_roster_format_comprehensive_workflow()`：完整工作流程測試
- **新增 TestCrossVillageProcessing 測試類別** (`tests/test_village_processor.py`) 🆕：
  - `test_cross_village_parameter_initialization()`：測試 include_cross_village 參數初始化
  - `test_cross_village_address_detection_enabled()`：測試跨村里地址偵測（啟用模式）
  - `test_cross_village_address_detection_disabled()`：測試跨村里地址偵測（預設模式）
  - `test_standardize_cross_village_address()`：測試跨村里地址標準化邏輯
  - `test_extract_village_name()`：測試村里名稱提取功能
  - `test_query_address_coordinates_with_target_village()`：測試指定村里座標查詢
  - `test_process_data_with_cross_village_enabled()`：測試跨村里完整資料處理流程
  - `test_export_cross_village_addresses()`：測試跨村里地址 CSV 導出
  - `test_roster_format_with_variable_columns()`：測試不同欄位數量的名冊格式處理
  - `test_comprehensive_cross_village_workflow()`：綜合跨村里工作流程測試
- **測試結果**：29 個測試全部通過（新增 11 個跨村里功能測試），確保新功能穩定性與向後相容性

### Technical Details

#### 🏗️ 架構改進
- **新增 importers 模組**：專門處理各種格式的資料導入
- **資料流程優化**：CSV → CSVGroupRow → RouteGroup → 視覺化
- **錯誤處理強化**：從檔案讀取到視覺化生成的完整錯誤處理鏈

#### 🧪 相容性
- **向後相容**：既有的 `visualize` 命令功能完全不受影響
- **編碼支援**：支援 UTF-8 和 UTF-8 BOM 編碼的 CSV 檔案
- **Python 版本**：維持 Python 3.11+ 需求

### Use Cases

#### 🎯 應用場景擴充
1. **CSV 輸入分組工作流** 🆕：
   ```bash
   # 從 CSV 檔案直接進行分組
   uv run survey-grouping create-groups --input-csv data/addresses.csv --output-file result.csv
   
   # 自訂分組大小
   uv run survey-grouping create-groups --input-csv data/addresses.csv --target-size 30
   
   # 輸出不同格式
   uv run survey-grouping create-groups --input-csv addresses.csv --output-format excel
   ```

2. **分組微調工作流**：
   ```bash
   # 1. 生成初始分組
   uv run survey-grouping create-groups 七股區 西寮里 --output-format csv
   
   # 2. 手動調整 CSV 檔案中的分組分配
   
   # 3. 重新生成視覺化
   uv run survey-grouping visualize-from-csv output/調整後的分組.csv
   ```

3. **無資料庫環境使用** 🆕：
   ```bash
   # 適合小型專案或快速原型開發
   uv run survey-grouping create-groups --input-csv simple_addresses.csv
   ```

5. **VillageProcessor Excel 處理工作流** 🆕：
   ```bash
   # 處理頂山里 Excel 數據
   uv run python src/survey_grouping/processors/village_processor.py \
     --district 七股區 --village 頂山里 \
     --excel-path data/頂山里200戶.xlsx
   
   # 處理鹽水區多個村里（單工作表格式）
   uv run python src/survey_grouping/processors/village_processor.py \
     --district 鹽水區 --village 文昌里 \
     --excel-path data/鹽水區.xlsx
   
   # 處理七股里名冊格式
   uv run python src/survey_grouping/processors/village_processor.py \
     --district 七股區 --village 七股里 \
     --excel-path data/七股里.xlsx
   
   # 🆕 跨村里處理模式（處理同區其他村里地址）
   uv run python src/survey_grouping/processors/village_processor.py \
     --district 七股區 --village 七股里 \
     --excel-path data/七股里.xlsx \
     --include-cross-village
   
   # 檢查處理結果和匹配率
   # 匹配率從原本的 90.6% 提升至 96.9%（dash-to-zhi 修復後）
   # 跨村里模式額外提供塩埕里等其他村里地址的座標匹配
   ```

4. **批次視覺化處理**：
   ```bash
   # 為多個預先準備的 CSV 檔案生成地圖
   for file in *.csv; do
     uv run survey-grouping visualize-from-csv "$file" --output-dir "maps_$(basename "$file" .csv)"
   done
   ```

---

## [Previous Versions]

### [0.2.0] - 2024-xx-xx
- feat(visualization): implement interactive map visualization with Folium
- test(coverage): improve test coverage from 55% to 63%
- chore(gitignore): add map visualization output directories to gitignore

### [0.1.0] - 2024-xx-xx
- Initial release with basic grouping functionality
- PostGIS spatial database integration
- CLI interface with Typer
- Multiple export formats support