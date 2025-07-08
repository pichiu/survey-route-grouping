# 使用 uv 管理專案

本專案已配置為使用 [uv](https://docs.astral.sh/uv/) 作為 Python 包管理工具。uv 是一個快速的 Python 包管理器，與現有的 Python 生態系統完全兼容。

## 安裝 uv

如果您還沒有安裝 uv，請參考 [官方安裝指南](https://docs.astral.sh/uv/getting-started/installation/)：

```bash
# macOS 和 Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 使用 pip 安裝
pip install uv
```

## 專案設置

### 1. 同步依賴項
```bash
# 安裝所有生產依賴項
uv sync

# 安裝包含開發依賴項
uv sync --all-extras

# 或者安裝特定的可選依賴組
uv sync --extra dev
uv sync --extra test
uv sync --extra docs
```

### 2. 添加新依賴項
```bash
# 添加生產依賴項
uv add requests

# 添加開發依賴項
uv add --dev pytest

# 添加到特定的可選依賴組
uv add --optional-group test pytest-asyncio
```

### 3. 移除依賴項
```bash
# 移除依賴項
uv remove requests

# 移除開發依賴項
uv remove --dev pytest
```

## 運行命令

### 在虛擬環境中運行命令
```bash
# 運行 Python 腳本
uv run python src/survey_grouping/main.py

# 運行已安裝的命令行工具
uv run survey-grouping --help

# 運行測試
uv run pytest

# 運行代碼格式化
uv run black src tests

# 運行代碼檢查
uv run ruff check src tests

# 運行類型檢查
uv run mypy src
```

### 開發工作流程

#### 代碼質量檢查
```bash
# 格式化代碼
uv run black src tests

# 檢查代碼風格
uv run ruff check src tests

# 自動修復可修復的問題
uv run ruff check --fix src tests

# 類型檢查
uv run mypy src
```

#### 測試
```bash
# 運行所有測試
uv run pytest

# 運行測試並生成覆蓋率報告
uv run pytest --cov=src/survey_grouping --cov-report=html

# 運行特定測試
uv run pytest tests/test_specific.py

# 運行標記的測試
uv run pytest -m "not slow"
```

#### 文檔
```bash
# 構建文檔
uv run mkdocs build

# 本地預覽文檔
uv run mkdocs serve
```

## 專案結構

```
survey-route-grouping/
├── pyproject.toml          # 專案配置和依賴項
├── uv.lock                 # 鎖定的依賴項版本（自動生成）
├── .python-version         # Python 版本（可選）
├── src/
│   └── survey_grouping/    # 主要源代碼
├── tests/                  # 測試文件
└── docs/                   # 文檔文件
```

## 可選依賴組

本專案定義了以下可選依賴組：

- **dev**: 完整的開發環境（包含測試、代碼檢查、文檔工具）
- **test**: 測試工具（pytest、coverage 等）
- **lint**: 代碼檢查工具（black、ruff、mypy）
- **docs**: 文檔生成工具（mkdocs）
- **all**: 包含所有上述工具

## 常用命令速查

| 操作 | 命令 |
|------|------|
| 初始化專案 | `uv sync` |
| 添加依賴項 | `uv add <package>` |
| 添加開發依賴項 | `uv add --dev <package>` |
| 移除依賴項 | `uv remove <package>` |
| 運行腳本 | `uv run <command>` |
| 運行測試 | `uv run pytest` |
| 格式化代碼 | `uv run black .` |
| 檢查代碼 | `uv run ruff check .` |
| 類型檢查 | `uv run mypy src` |
| 構建專案 | `uv build` |

## 與其他工具的比較

| 功能 | uv | pip | poetry | pdm |
|------|----|----|--------|-----|
| 依賴解析速度 | 🚀 極快 | 🐌 慢 | 🚶 中等 | 🚶 中等 |
| 鎖定文件 | ✅ uv.lock | ❌ | ✅ poetry.lock | ✅ pdm.lock |
| PEP 621 支援 | ✅ | ❌ | 部分 | ✅ |
| 虛擬環境管理 | ✅ | ❌ | ✅ | ✅ |
| 構建支援 | ✅ | ❌ | ✅ | ✅ |

## 疑難排解

### 常見問題

1. **虛擬環境問題**
   ```bash
   # 重新創建虛擬環境
   uv sync --reinstall
   ```

2. **依賴衝突**
   ```bash
   # 查看依賴樹
   uv tree
   
   # 強制重新解析依賴
   uv lock --upgrade
   ```

3. **Python 版本問題**
   ```bash
   # 指定 Python 版本
   uv python install 3.11
   uv sync --python 3.11
   ```

### 獲取幫助

```bash
# 查看 uv 幫助
uv --help

# 查看特定命令的幫助
uv sync --help
uv add --help
```

## 更多資源

- [uv 官方文檔](https://docs.astral.sh/uv/)
- [uv GitHub 倉庫](https://github.com/astral-sh/uv)
- [Python 包管理最佳實踐](https://packaging.python.org/)
