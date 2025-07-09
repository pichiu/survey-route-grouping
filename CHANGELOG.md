# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
  - `validate_csv_format()` 方法：CSV 格式驗證
  - `import_from_csv()` 方法：完整的 CSV 導入流程
  - `convert_to_route_groups()` 方法：轉換為 RouteGroup 物件

### Changed

#### 🎨 視覺化邏輯優化
- **FoliumRenderer 改進** (`src/survey_grouping/visualizers/folium_renderer.py`)：
  - `_add_route_line()` 方法：只在有路線順序時繪製連線
  - `_add_detailed_route()` 方法：只在有路線順序時顯示詳細路線和箭頭
  - `_add_ordered_markers()` 方法：智慧切換有序/無序標記顯示
  - 新增 `_add_group_markers_to_map()` 方法：處理無順序的一般標記

#### 📋 命令列介面擴充
- **main.py 更新**：
  - 新增 `visualize-from-csv` 命令及其參數選項
  - 整合 CSVImporter 到主要 CLI 介面
  - 改進錯誤處理和使用者提示訊息

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
1. **分組微調工作流**：
   ```bash
   # 1. 生成初始分組
   uv run survey-grouping create-groups 七股區 西寮里 --output-format csv
   
   # 2. 手動調整 CSV 檔案中的分組分配
   
   # 3. 重新生成視覺化
   uv run survey-grouping visualize-from-csv output/調整後的分組.csv
   ```

2. **簡化資料處理**：
   ```bash
   # 只有基本資訊的 CSV 也能直接視覺化
   uv run survey-grouping visualize-from-csv simple_groups.csv
   ```

3. **批次視覺化處理**：
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