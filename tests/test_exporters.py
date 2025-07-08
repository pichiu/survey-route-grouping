"""匯出器測試

測試 CSV、JSON、Excel 匯出功能。
"""

import json
import tempfile
from pathlib import Path
import pandas as pd
from survey_grouping.exporters.csv_exporter import CSVExporter
from survey_grouping.exporters.json_exporter import JSONExporter
from survey_grouping.exporters.excel_exporter import ExcelExporter


class TestCSVExporter:
    """CSV 匯出器測試"""

    def test_export_groups(self, sample_grouping_result, temp_output_dir):
        """測試分組匯出到 CSV"""
        output_path = temp_output_dir / "groups.csv"

        success = CSVExporter.export_groups(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        df = pd.read_csv(output_path)
        assert len(df) == 5  # 總共 5 個地址
        assert "分組編號" in df.columns
        assert "完整地址" in df.columns

    def test_export_grouping_result(self, sample_grouping_result, temp_output_dir):
        """測試完整分組結果匯出"""
        output_path = temp_output_dir / "result.csv"

        success = CSVExporter.export_grouping_result(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

    def test_export_summary(self, sample_grouping_result, temp_output_dir):
        """測試摘要匯出"""
        output_path = temp_output_dir / "summary.csv"

        success = CSVExporter.export_summary(sample_grouping_result, str(output_path))

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        df = pd.read_csv(output_path)
        assert len(df) == 2  # 兩個分組
        assert "分組編號" in df.columns
        assert "分組大小" in df.columns

    def test_export_addresses_only(self, sample_grouping_result, temp_output_dir):
        """測試僅匯出地址"""
        output_path = temp_output_dir / "addresses.csv"

        success = CSVExporter.export_addresses_only(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

    def test_create_route_sheets(self, sample_grouping_result, temp_output_dir):
        """測試建立路線工作表"""
        created_files = CSVExporter.create_route_sheets(
            sample_grouping_result, str(temp_output_dir)
        )

        assert len(created_files) == 2  # 兩個分組
        for file_path in created_files:
            assert Path(file_path).exists()


class TestJSONExporter:
    """JSON 匯出器測試"""

    def test_export_groups(self, sample_grouping_result, temp_output_dir):
        """測試分組匯出到 JSON"""
        output_path = temp_output_dir / "groups.json"

        success = JSONExporter.export_groups(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2  # 兩個分組
        assert "group_id" in data[0]
        assert "addresses" in data[0]

    def test_export_grouping_result(self, sample_grouping_result, temp_output_dir):
        """測試完整分組結果匯出"""
        output_path = temp_output_dir / "result.json"

        success = JSONExporter.export_grouping_result(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "groups" in data
        assert "coverage_summary" in data

    def test_export_geojson(self, sample_grouping_result, temp_output_dir):
        """測試 GeoJSON 匯出"""
        output_path = temp_output_dir / "groups.geojson"

        success = JSONExporter.export_geojson(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert len(data["features"]) == 5  # 5 個地址

    def test_export_route_optimization_data(
        self, sample_grouping_result, temp_output_dir
    ):
        """測試路線優化資料匯出"""
        output_path = temp_output_dir / "route_data.json"

        success = JSONExporter.export_route_optimization_data(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2  # 兩個分組
        assert "distance_matrix" in data[0]
        assert "optimized_route" in data[0]

    def test_export_statistics_summary(self, sample_grouping_result, temp_output_dir):
        """測試統計摘要匯出"""
        output_path = temp_output_dir / "stats.json"

        success = JSONExporter.export_statistics_summary(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "basic_info" in data
        assert "group_size_analysis" in data
        assert "distance_analysis" in data


class TestExcelExporter:
    """Excel 匯出器測試"""

    def test_export_groups(self, sample_grouping_result, temp_output_dir):
        """測試分組匯出到 Excel"""
        output_path = temp_output_dir / "groups.xlsx"

        success = ExcelExporter.export_groups(
            sample_grouping_result.groups, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        df = pd.read_excel(output_path)
        assert len(df) == 5  # 總共 5 個地址
        assert "分組編號" in df.columns

    def test_export_grouping_result_multi_sheet(
        self, sample_grouping_result, temp_output_dir
    ):
        """測試多工作表匯出"""
        output_path = temp_output_dir / "result_multi.xlsx"

        success = ExcelExporter.export_grouping_result_multi_sheet(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查工作表
        excel_file = pd.ExcelFile(output_path)
        assert "分組摘要" in excel_file.sheet_names
        assert "詳細地址" in excel_file.sheet_names
        assert "統計資訊" in excel_file.sheet_names

    def test_create_route_workbook(self, sample_grouping_result, temp_output_dir):
        """測試路線工作簿建立"""
        output_path = temp_output_dir / "routes.xlsx"

        success = ExcelExporter.create_route_workbook(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查工作表
        excel_file = pd.ExcelFile(output_path)
        assert "總覽" in excel_file.sheet_names
        assert len(excel_file.sheet_names) == 3  # 總覽 + 2個路線工作表

    def test_export_comparison_analysis(self, sample_grouping_result, temp_output_dir):
        """測試比較分析匯出"""
        output_path = temp_output_dir / "comparison.xlsx"

        # 建立多個結果進行比較
        results = [sample_grouping_result, sample_grouping_result]

        success = ExcelExporter.export_comparison_analysis(results, str(output_path))

        assert success is True
        assert output_path.exists()

    def test_export_quality_report(self, sample_grouping_result, temp_output_dir):
        """測試品質報告匯出"""
        output_path = temp_output_dir / "quality.xlsx"

        success = ExcelExporter.export_quality_report(
            sample_grouping_result, str(output_path)
        )

        assert success is True
        assert output_path.exists()

        # 檢查工作表
        excel_file = pd.ExcelFile(output_path)
        assert "品質評估" in excel_file.sheet_names


class TestExporterErrorHandling:
    """匯出器錯誤處理測試"""

    def test_csv_export_invalid_path(self, sample_grouping_result):
        """測試 CSV 匯出無效路徑"""
        invalid_path = "/invalid/path/file.csv"

        success = CSVExporter.export_groups(sample_grouping_result.groups, invalid_path)

        assert success is False

    def test_json_export_invalid_path(self, sample_grouping_result):
        """測試 JSON 匯出無效路徑"""
        invalid_path = "/invalid/path/file.json"

        success = JSONExporter.export_groups(
            sample_grouping_result.groups, invalid_path
        )

        assert success is False

    def test_excel_export_invalid_path(self, sample_grouping_result):
        """測試 Excel 匯出無效路徑"""
        invalid_path = "/invalid/path/file.xlsx"

        success = ExcelExporter.export_groups(
            sample_grouping_result.groups, invalid_path
        )

        assert success is False

    def test_export_empty_groups(self, temp_output_dir):
        """測試匯出空分組"""
        output_path = temp_output_dir / "empty.csv"

        success = CSVExporter.export_groups([], str(output_path))

        assert success is True
        assert output_path.exists()

        # 檢查檔案內容
        df = pd.read_csv(output_path)
        assert len(df) == 0  # 空檔案
