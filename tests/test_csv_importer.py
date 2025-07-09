"""CSV 導入器測試模組"""

import pytest
import csv
import tempfile
from pathlib import Path
from datetime import datetime

from src.survey_grouping.importers.csv_importer import CSVImporter, CSVGroupRow
from src.survey_grouping.models.group import RouteGroup
from src.survey_grouping.models.address import Address


class TestCSVGroupRow:
    """CSVGroupRow 模型測試"""
    
    def test_csv_group_row_creation(self):
        """測試 CSVGroupRow 建立"""
        row_data = {
            '分組編號': '七股區西寮里-01',
            '分組大小': 35,
            '目標大小': 35,
            '預估距離(公尺)': 666.41,
            '預估時間(分鐘)': 112,
            '地址ID': 182395,
            '完整地址': '西寮1號之1',
            '區域': '七股區',
            '村里': '西寮里',
            '鄰別': 1,
            '經度': 120.096909,
            '緯度': 23.169889,
            '訪問順序': 3
        }
        
        row = CSVGroupRow(**row_data)
        
        assert row.分組編號 == '七股區西寮里-01'
        assert row.分組大小 == 35
        assert row.預估距離_公尺 == 666.41
        assert row.預估時間_分鐘 == 112
        assert row.地址ID == 182395
        assert row.完整地址 == '西寮1號之1'
        assert row.經度 == 120.096909
        assert row.緯度 == 23.169889
        assert row.訪問順序 == 3

    def test_csv_group_row_optional_fields(self):
        """測試 CSVGroupRow 的 optional 欄位"""
        # 只提供必要欄位
        row_data = {
            '分組編號': '七股區西寮里-01',
            '完整地址': '西寮1號之1',
            '區域': '七股區',
            '村里': '西寮里',
            '鄰別': 1,
            '經度': 120.096909,
            '緯度': 23.169889
        }
        
        row = CSVGroupRow(**row_data)
        
        assert row.分組編號 == '七股區西寮里-01'
        assert row.分組大小 is None
        assert row.目標大小 is None
        assert row.預估距離_公尺 is None
        assert row.預估時間_分鐘 is None
        assert row.地址ID is None
        assert row.訪問順序 is None


class TestCSVImporter:
    """CSVImporter 類別測試"""
    
    @pytest.fixture
    def importer(self):
        """提供 CSVImporter 實例"""
        return CSVImporter()
    
    @pytest.fixture
    def sample_csv_content(self):
        """提供測試用的 CSV 內容"""
        return [
            ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度', '訪問順序'],
            ['七股區西寮里-01', '西寮1號', '七股區', '西寮里', '1', '120.096955', '23.169737', '1'],
            ['七股區西寮里-01', '西寮2號', '七股區', '西寮里', '1', '120.096739', '23.169929', '2'],
            ['七股區西寮里-02', '西寮22號', '七股區', '西寮里', '2', '120.096131', '23.171376', '1'],
            ['七股區西寮里-02', '西寮23號', '七股區', '西寮里', '2', '120.096239', '23.171444', '2']
        ]
    
    @pytest.fixture
    def minimal_csv_content(self):
        """提供最小 CSV 內容（沒有 optional 欄位）"""
        return [
            ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度'],
            ['七股區西寮里-01', '西寮1號', '七股區', '西寮里', '1', '120.096955', '23.169737'],
            ['七股區西寮里-01', '西寮2號', '七股區', '西寮里', '1', '120.096739', '23.169929']
        ]
    
    def create_temp_csv(self, content, encoding='utf-8'):
        """建立臨時 CSV 檔案"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', 
                                               delete=False, encoding=encoding)
        writer = csv.writer(temp_file)
        for row in content:
            writer.writerow(row)
        temp_file.close()
        return temp_file.name
    
    def test_validate_csv_format_valid(self, importer, sample_csv_content):
        """測試有效 CSV 格式驗證"""
        csv_file = self.create_temp_csv(sample_csv_content)
        
        try:
            is_valid, errors = importer.validate_csv_format(csv_file)
            assert is_valid is True
            assert len(errors) == 0
        finally:
            Path(csv_file).unlink()
    
    def test_validate_csv_format_missing_fields(self, importer):
        """測試缺少必要欄位的 CSV"""
        incomplete_content = [
            ['分組編號', '完整地址', '區域'],  # 缺少村里、鄰別、經度、緯度
            ['七股區西寮里-01', '西寮1號', '七股區']
        ]
        csv_file = self.create_temp_csv(incomplete_content)
        
        try:
            is_valid, errors = importer.validate_csv_format(csv_file)
            assert is_valid is False
            assert len(errors) > 0
            assert '缺少必要欄位' in errors[0]
        finally:
            Path(csv_file).unlink()
    
    def test_validate_csv_format_invalid_coordinates(self, importer):
        """測試無效座標的 CSV"""
        invalid_coords_content = [
            ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度'],
            ['七股區西寮里-01', '西寮1號', '七股區', '西寮里', '1', 'invalid', '23.169737']
        ]
        csv_file = self.create_temp_csv(invalid_coords_content)
        
        try:
            is_valid, errors = importer.validate_csv_format(csv_file)
            assert is_valid is False
            assert len(errors) > 0
            assert '經緯度格式錯誤' in errors[0]
        finally:
            Path(csv_file).unlink()
    
    def test_validate_csv_format_nonexistent_file(self, importer):
        """測試不存在的檔案"""
        is_valid, errors = importer.validate_csv_format('nonexistent.csv')
        assert is_valid is False
        assert len(errors) == 1
        assert '檔案不存在' in errors[0]
    
    def test_read_csv_file_success(self, importer, sample_csv_content):
        """測試成功讀取 CSV 檔案"""
        csv_file = self.create_temp_csv(sample_csv_content)
        
        try:
            rows = importer.read_csv_file(csv_file)
            assert len(rows) == 4
            
            # 檢查第一筆資料
            first_row = rows[0]
            assert first_row.分組編號 == '七股區西寮里-01'
            assert first_row.完整地址 == '西寮1號'
            assert first_row.訪問順序 == 1
            
            # 檢查第三筆資料（不同分組）
            third_row = rows[2]
            assert third_row.分組編號 == '七股區西寮里-02'
            assert third_row.完整地址 == '西寮22號'
        finally:
            Path(csv_file).unlink()
    
    def test_read_csv_file_with_bom(self, importer, sample_csv_content):
        """測試讀取帶 BOM 的 CSV 檔案"""
        csv_file = self.create_temp_csv(sample_csv_content, encoding='utf-8-sig')
        
        try:
            rows = importer.read_csv_file(csv_file)
            assert len(rows) == 4
            assert rows[0].分組編號 == '七股區西寮里-01'
        finally:
            Path(csv_file).unlink()
    
    def test_read_csv_file_minimal_format(self, importer, minimal_csv_content):
        """測試讀取最小格式的 CSV 檔案"""
        csv_file = self.create_temp_csv(minimal_csv_content)
        
        try:
            rows = importer.read_csv_file(csv_file)
            assert len(rows) == 2
            
            # 檢查 optional 欄位為 None
            first_row = rows[0]
            assert first_row.分組編號 == '七股區西寮里-01'
            assert first_row.完整地址 == '西寮1號'
            assert first_row.訪問順序 is None
            assert first_row.分組大小 is None
            assert first_row.地址ID is None
        finally:
            Path(csv_file).unlink()
    
    def test_group_rows_by_group_id(self, importer, sample_csv_content):
        """測試按分組編號分組"""
        csv_file = self.create_temp_csv(sample_csv_content)
        
        try:
            rows = importer.read_csv_file(csv_file)
            grouped = importer.group_rows_by_group_id(rows)
            
            assert len(grouped) == 2
            assert '七股區西寮里-01' in grouped
            assert '七股區西寮里-02' in grouped
            assert len(grouped['七股區西寮里-01']) == 2
            assert len(grouped['七股區西寮里-02']) == 2
        finally:
            Path(csv_file).unlink()
    
    def test_convert_to_route_groups(self, importer, sample_csv_content):
        """測試轉換為 RouteGroup 物件"""
        csv_file = self.create_temp_csv(sample_csv_content)
        
        try:
            rows = importer.read_csv_file(csv_file)
            grouped = importer.group_rows_by_group_id(rows)
            route_groups = importer.convert_to_route_groups(grouped)
            
            assert len(route_groups) == 2
            
            # 檢查第一個分組
            group1 = route_groups[0]
            assert isinstance(group1, RouteGroup)
            assert group1.group_id in ['七股區西寮里-01', '七股區西寮里-02']
            assert len(group1.addresses) == 2
            assert len(group1.route_order) == 2  # 應該有訪問順序
            
            # 檢查地址物件
            addr = group1.addresses[0]
            assert isinstance(addr, Address)
            assert addr.district == '七股區'
            assert addr.village == '西寮里'
            assert addr.has_valid_coordinates
        finally:
            Path(csv_file).unlink()
    
    def test_convert_to_route_groups_no_order(self, importer, minimal_csv_content):
        """測試轉換沒有順序的分組"""
        csv_file = self.create_temp_csv(minimal_csv_content)
        
        try:
            rows = importer.read_csv_file(csv_file)
            grouped = importer.group_rows_by_group_id(rows)
            route_groups = importer.convert_to_route_groups(grouped)
            
            assert len(route_groups) == 1
            
            group = route_groups[0]
            assert group.group_id == '七股區西寮里-01'
            assert len(group.addresses) == 2
            assert len(group.route_order) == 0  # 沒有訪問順序
        finally:
            Path(csv_file).unlink()
    
    def test_import_from_csv_complete_workflow(self, importer, sample_csv_content):
        """測試完整的 CSV 導入工作流程"""
        csv_file = self.create_temp_csv(sample_csv_content)
        
        try:
            grouping_result = importer.import_from_csv(csv_file)
            
            # 檢查 GroupingResult
            assert grouping_result.district == '七股區'
            assert grouping_result.village == '西寮里'
            assert grouping_result.total_addresses == 4
            assert grouping_result.total_groups == 2
            assert isinstance(grouping_result.created_at, datetime)
            
            # 檢查統計資訊
            assert grouping_result.avg_group_size == 2.0
            assert grouping_result.min_group_size == 2
            assert grouping_result.max_group_size == 2
        finally:
            Path(csv_file).unlink()
    
    def test_import_from_csv_empty_file(self, importer):
        """測試空的 CSV 檔案"""
        empty_content = [
            ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度']
        ]
        csv_file = self.create_temp_csv(empty_content)
        
        try:
            with pytest.raises(ValueError, match="CSV 檔案為空或無有效資料"):
                importer.import_from_csv(csv_file)
        finally:
            Path(csv_file).unlink()
    
    def test_read_csv_file_invalid_data(self, importer):
        """測試無效資料的 CSV 檔案"""
        invalid_content = [
            ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度'],
            ['七股區西寮里-01', '西寮1號', '七股區', '西寮里', '1', 'invalid_lng', '23.169737']
        ]
        csv_file = self.create_temp_csv(invalid_content)
        
        try:
            with pytest.raises(ValueError, match="第 .* 行的 .* 必須是有效數值"):
                importer.read_csv_file(csv_file)
        finally:
            Path(csv_file).unlink()


@pytest.mark.integration
class TestCSVImporterIntegration:
    """CSV 導入器整合測試"""
    
    def test_real_csv_format_compatibility(self):
        """測試與實際 CSV 格式的相容性"""
        # 模擬實際的完整格式 CSV
        real_csv_content = [
            ['分組編號', '分組大小', '目標大小', '預估距離(公尺)', '預估時間(分鐘)', 
             '地址ID', '完整地址', '區域', '村里', '鄰別', '經度', '緯度', '訪問順序'],
            ['七股區西寮里-01', '35', '35', '666.41', '112', '182395', 
             '西寮1號之1', '七股區', '西寮里', '1', '120.096909', '23.169889', '3'],
            ['七股區西寮里-01', '35', '35', '666.41', '112', '182396', 
             '西寮1號', '七股區', '西寮里', '1', '120.096955', '23.169737', '2']
        ]
        
        importer = CSVImporter()
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', 
                                               delete=False, encoding='utf-8')
        writer = csv.writer(temp_file)
        for row in real_csv_content:
            writer.writerow(row)
        temp_file.close()
        
        try:
            # 測試格式驗證
            is_valid, errors = importer.validate_csv_format(temp_file.name)
            assert is_valid is True
            
            # 測試完整導入
            grouping_result = importer.import_from_csv(temp_file.name)
            assert grouping_result.total_addresses == 2
            assert grouping_result.total_groups == 1
            
            # 檢查路線順序
            group = grouping_result.groups[0]
            assert len(group.route_order) == 2
            assert group.estimated_distance == 666.41
            assert group.estimated_time == 112
            assert group.target_size == 35
            assert group.actual_size == 35
            
        finally:
            Path(temp_file.name).unlink()