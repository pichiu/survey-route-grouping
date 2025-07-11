"""
Tests for VillageProcessor
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import tempfile
import os

from survey_grouping.processors.village_processor import (
    VillageProcessor,
    convert_fullwidth_to_halfwidth,
    extract_neighborhood_from_address,
)


class TestVillageProcessor:
    """Test cases for VillageProcessor"""
    
    @pytest.fixture
    def mock_supabase_response(self):
        """Mock Supabase response for testing"""
        def _response(data):
            mock_response = Mock()
            mock_response.data = data
            return mock_response
        return _response
    
    @pytest.fixture
    def processor(self):
        """Create a VillageProcessor instance for testing"""
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            return VillageProcessor("七股區", "頂山里")
    
    def test_query_address_coordinates_exact_match(self, processor, mock_supabase_response):
        """Test exact address matching returns coordinates"""
        # Mock successful response
        mock_data = [{"x_coord": 120.112034, "y_coord": 23.180486}]
        processor.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_supabase_response(mock_data)
        
        result = processor.query_address_coordinates("頂山13號")
        
        assert result == (120.112034, 23.180486)
    
    def test_query_address_coordinates_no_match(self, processor, mock_supabase_response):
        """Test address not found returns None"""
        # Mock empty response
        processor.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_supabase_response([])
        
        result = processor.query_address_coordinates("頂山2號之3")
        
        assert result is None
    
    def test_query_address_coordinates_no_fuzzy_matching(self, processor, mock_supabase_response):
        """Test that fuzzy matching is disabled"""
        # Mock empty response for exact match
        processor.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_supabase_response([])
        
        result = processor.query_address_coordinates("頂山2號之3")
        
        # Should return None instead of attempting fuzzy match
        assert result is None
        
        # Verify that only exact match query was called (no ilike query)
        select_mock = processor.supabase.table.return_value.select
        assert select_mock.call_count == 1
        select_mock.assert_called_with("x_coord, y_coord")
    
    def test_process_data_with_mixed_matches(self, processor):
        """Test processing data with both matched and unmatched addresses"""
        # Mock Excel data
        mock_data = [
            {
                "serial_number": "13",
                "name": "吳靜媚", 
                "original_address": "頂山13號",
                "neighborhood": 1
            },
            {
                "serial_number": "4",
                "name": "陳金鐘",
                "original_address": "頂山2號之3", 
                "neighborhood": 1
            }
        ]
        
        def mock_query_coordinates(address):
            if address == "頂山13號":
                return (120.112034, 23.180486)
            elif address == "頂山2號之3":
                return None
            return None
        
        with patch.object(processor, 'read_excel_data', return_value=mock_data), \
             patch.object(processor, 'query_address_coordinates', side_effect=mock_query_coordinates), \
             patch('survey_grouping.processors.village_processor.standardize_village_address', side_effect=lambda x, y: x):
            
            processed_data, unmatched = processor.process_data("dummy_path.xlsx")
            
            # Should have 2 processed items (both matched and unmatched)
            assert len(processed_data) == 2
            
            # Should have 1 unmatched item
            assert len(unmatched) == 1
            
            # Check matched item has coordinates
            matched_item = next(item for item in processed_data if item["name"] == "吳靜媚")
            assert matched_item["longitude"] == 120.112034
            assert matched_item["latitude"] == 23.180486
            
            # Check unmatched item has None coordinates
            unmatched_item = next(item for item in processed_data if item["name"] == "陳金鐘")
            assert unmatched_item["longitude"] is None
            assert unmatched_item["latitude"] is None
            
            # Check unmatched list
            assert unmatched[0]["name"] == "陳金鐘"
            assert unmatched[0]["original_address"] == "頂山2號之3"
    
    def test_export_unmatched_report(self, processor):
        """Test unmatched address report generation"""
        unmatched_data = [
            {
                "serial_number": "4",
                "name": "陳金鐘",
                "neighborhood": 1,
                "original_address": "頂山里2-3號",
                "standardized_address": "頂山2號之3"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor.export_unmatched_report(unmatched_data, tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify content
            df = pd.read_csv(tmp_path, encoding='utf-8-sig')
            assert len(df) == 1
            assert list(df.columns) == ["序號", "姓名", "鄰別", "原始地址", "標準化地址"]
            assert df.iloc[0]["序號"] == 4
            assert df.iloc[0]["姓名"] == "陳金鐘"
            assert df.iloc[0]["原始地址"] == "頂山里2-3號"
            assert df.iloc[0]["標準化地址"] == "頂山2號之3"
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_export_unmatched_report_empty(self, processor):
        """Test unmatched report with no unmatched addresses"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor.export_unmatched_report([], tmp_path)
            
            # Should not create file for empty data
            # (based on the implementation that skips export when no unmatched addresses)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_single_sheet_format_detection(self, mock_supabase_response):
        """Test automatic detection of single sheet format"""
        # Create processor for matching data
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            processor = VillageProcessor("鹽水區", "文昌里")
        
        # Mock Excel file with single sheet format
        single_sheet_data = pd.DataFrame([
            {"編號": 1, "行政區": "鹽水區", "里": "文昌里", "鄰": 11, "地址": "羊稠厝22號", "姓名": "邱樹"},
            {"編號": 2, "行政區": "鹽水區", "里": "文昌里", "鄰": 6, "地址": "番子寮2號", "姓名": "蔡澄山"},
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            # Mock ExcelFile
            mock_excel_file.return_value.sheet_names = ["鹽水區"]
            
            # Mock read_excel calls
            mock_read_excel.return_value = single_sheet_data
            
            # Test that it detects single sheet format automatically
            data = processor.read_excel_data("dummy_path.xlsx")
            
            # Should have called read_excel twice (once for detection, once for processing)
            assert mock_read_excel.call_count == 2
            
            # Should return data in correct format
            assert len(data) == 2
            assert data[0]["neighborhood"] == 11
            assert data[0]["original_address"] == "羊稠厝22號"
            assert data[1]["neighborhood"] == 6
            assert data[1]["original_address"] == "番子寮2號"

    def test_multi_sheet_format_with_mapping(self, processor, mock_supabase_response):
        """Test multi-sheet format still works with neighborhood_mapping"""
        # Mock Excel file with multi-sheet format
        multi_sheet_data = pd.DataFrame([
            {"col1": "序號", "col2": "姓名", "col3": "地址"},
            {"col1": "1", "col2": "陳金鐘", "col3": "頂山2號之3"},
        ])
        
        neighborhood_mapping = {"第一鄰": 1}
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            # Mock ExcelFile
            mock_excel_file.return_value.sheet_names = ["第一鄰"]
            
            # Mock read_excel calls - first call has no '鄰' column
            mock_read_excel.return_value = multi_sheet_data
            
            # Test with neighborhood_mapping provided
            data = processor.read_excel_data("dummy_path.xlsx", neighborhood_mapping)
            
            # Should process as multi-sheet format
            assert len(data) == 1
            assert data[0]["neighborhood"] == 1
            assert data[0]["original_address"] == "頂山2號之3"

    def test_export_to_csv_with_none_coordinates(self, processor):
        """Test CSV export handles None coordinates correctly"""
        processed_data = [
            {
                "serial_number": "13",
                "name": "吳靜媚",
                "full_address": "頂山13號",
                "district": "七股區", 
                "village": "頂山里",
                "neighborhood": 1,
                "longitude": 120.112034,
                "latitude": 23.180486
            },
            {
                "serial_number": "4", 
                "name": "陳金鐘",
                "full_address": "頂山2號之3",
                "district": "七股區",
                "village": "頂山里", 
                "neighborhood": 1,
                "longitude": None,
                "latitude": None
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor.export_to_csv(processed_data, tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify content
            df = pd.read_csv(tmp_path, encoding='utf-8-sig')
            assert len(df) == 2
            
            # Check matched item
            matched_row = df[df["姓名"] == "吳靜媚"].iloc[0]
            assert matched_row["經度"] == 120.112034
            assert matched_row["緯度"] == 23.180486
            
            # Check unmatched item (should have empty coordinates)
            unmatched_row = df[df["姓名"] == "陳金鐘"].iloc[0]
            assert pd.isna(unmatched_row["經度"])
            assert pd.isna(unmatched_row["緯度"])
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestUtilityFunctions:
    """Test cases for utility functions"""
    
    def test_convert_fullwidth_to_halfwidth(self):
        """Test full-width to half-width number conversion"""
        # Test full-width numbers
        assert convert_fullwidth_to_halfwidth("１２３４５") == "12345"
        assert convert_fullwidth_to_halfwidth("６７８９０") == "67890"
        
        # Test mixed content
        assert convert_fullwidth_to_halfwidth("臺南市七股區七股里１３鄰七股１２３－１２號") == "臺南市七股區七股里13鄰七股123－12號"
        
        # Test no full-width numbers
        assert convert_fullwidth_to_halfwidth("七股123號") == "七股123號"
        
        # Test empty string
        assert convert_fullwidth_to_halfwidth("") == ""
        assert convert_fullwidth_to_halfwidth(None) is None
    
    def test_extract_neighborhood_from_address(self):
        """Test neighborhood extraction from full address"""
        # Test normal cases
        assert extract_neighborhood_from_address("臺南市七股區七股里13鄰七股123號") == 13
        assert extract_neighborhood_from_address("臺南市七股區七股里1鄰七股74號之1") == 1
        assert extract_neighborhood_from_address("臺南市七股區七股里8鄰七股145號") == 8
        
        # Test edge cases
        assert extract_neighborhood_from_address("七股123號") is None
        assert extract_neighborhood_from_address("") is None
        assert extract_neighborhood_from_address(None) is None
        
        # Test with full-width numbers
        assert extract_neighborhood_from_address("臺南市七股區七股里１３鄰七股123號") == 13


class TestRosterFormatProcessing:
    """Test cases for roster format processing"""
    
    @pytest.fixture
    def processor(self):
        """Create a VillageProcessor instance for testing"""
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            return VillageProcessor("七股區", "七股里")
    
    def test_roster_format_detection(self, processor):
        """Test automatic detection of roster format"""
        # Mock roster format data
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "吳孟淵", "臺南市七股區七股里13鄰七股123號之12"],
            [2, "臺南市七股區七股里", "王明洲", "臺南市七股區七股里8鄰七股74號之1"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            # Mock ExcelFile
            mock_excel_file.return_value.sheet_names = ["七股里"]
            
            # Mock read_excel calls
            mock_read_excel.return_value = roster_data
            
            # Test that it detects roster format automatically
            data = processor.read_excel_data("dummy_path.xlsx")
            
            # Should detect roster format and process data
            assert len(data) == 2
            assert data[0]["name"] == "吳孟淵"
            assert data[0]["neighborhood"] == 13
            assert data[0]["standardized_address"] == "七股123號之12"
            assert data[1]["name"] == "王明洲"
            assert data[1]["neighborhood"] == 8
            assert data[1]["standardized_address"] == "七股74號之1"
    
    def test_roster_format_with_fullwidth_numbers(self, processor):
        """Test roster format with full-width numbers"""
        # Mock roster data with full-width numbers
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "測試人員", "臺南市七股區七股里１３鄰七股１２３號之１２"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            data = processor.read_excel_data("dummy_path.xlsx")
            
            assert len(data) == 1
            assert data[0]["name"] == "測試人員"
            assert data[0]["neighborhood"] == 13
            assert data[0]["standardized_address"] == "七股123號之12"
    
    def test_roster_format_cross_district_filtering(self, processor):
        """Test roster format filters out cross-district addresses"""
        # Mock roster data with cross-district addresses
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "有效地址", "臺南市七股區七股里13鄰七股123號"],
            [2, "臺南市七股區七股里", "跨區地址", "臺南市七股區塩埕里6鄰鹽埕237號之3"],
            [3, "臺南市七股區七股里", "跨區地址2", "臺南市七股區七股116號之19"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            data = processor.read_excel_data("dummy_path.xlsx")
            
            # Should only include valid addresses for the target district and village
            assert len(data) == 1
            assert data[0]["name"] == "有效地址"
            assert data[0]["standardized_address"] == "七股123號"
            
            # Should have recorded invalid addresses
            assert hasattr(processor, 'invalid_addresses')
            assert len(processor.invalid_addresses) == 2
            assert processor.invalid_addresses[0]["name"] == "跨區地址"
            assert processor.invalid_addresses[1]["name"] == "跨區地址2"
    
    def test_standardize_roster_address_dash_to_zhi_conversion(self, processor):
        """Test critical dash-to-zhi conversion in roster format"""
        # Test the specific case that was failing
        full_address = "臺南市七股區七股里8鄰七股74-1號"
        result = processor._standardize_roster_address(full_address)
        
        # Should convert 74-1號 to 74號之1
        assert result == "七股74號之1"
        
        # Test other dash-to-zhi cases
        test_cases = [
            ("臺南市七股區七股里13鄰七股123-12號", "七股123號之12"),
            ("臺南市七股區七股里2鄰七股22-4號", "七股22號之4"),
            ("臺南市七股區七股里5鄰七股116-19號", "七股116號之19"),
        ]
        
        for input_addr, expected in test_cases:
            result = processor._standardize_roster_address(input_addr)
            assert result == expected, f"Failed for {input_addr}: got {result}, expected {expected}"
    
    def test_export_invalid_addresses_report(self, processor):
        """Test invalid addresses report generation"""
        # Set up invalid addresses
        processor.invalid_addresses = [
            {
                "serial_number": "30",
                "name": "黃文騫",
                "raw_address": "臺南市七股區塩埕里6鄰鹽埕237號之3",
                "reason": "非七股區七股里地址"
            },
            {
                "serial_number": "34",
                "name": "吳國民",
                "raw_address": "臺南市七股區七股116號之19",
                "reason": "非七股區七股里地址"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor.export_invalid_addresses(tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify content
            df = pd.read_csv(tmp_path, encoding='utf-8-sig')
            assert len(df) == 2
            assert list(df.columns) == ["序號", "姓名", "原始地址", "問題原因"]
            assert df.iloc[0]["序號"] == 30  # CSV reading converts to int
            assert df.iloc[0]["姓名"] == "黃文騫"
            assert df.iloc[0]["問題原因"] == "非七股區七股里地址"
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_export_invalid_addresses_empty(self, processor):
        """Test invalid addresses export with no invalid addresses"""
        # No invalid addresses set
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor.export_invalid_addresses(tmp_path)
            
            # Should not create file or should handle gracefully
            # (based on the implementation that logs info when no invalid addresses)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_roster_format_comprehensive_workflow(self, processor):
        """Test complete workflow with roster format including critical fixes"""
        # Mock comprehensive roster data
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "吳孟淵", "臺南市七股區七股里13鄰七股123號之12"],
            [6, "臺南市七股區七股里", "王明洲", "臺南市七股區七股里8鄰七股74-1號"],  # Critical test case
            [30, "臺南市七股區七股里", "黃文騫", "臺南市七股區塩埕里6鄰鹽埕237號之3"],  # Cross-district
            [33, "臺南市七股區七股里", "黃明通", "臺南市七股區七股里7鄰5-2號"],  # Should be unmatched
        ])
        
        def mock_query_coordinates(address):
            """Mock coordinate query with specific responses"""
            if address == "七股123號之12":
                return (120.130496, 23.135225)
            elif address == "七股74號之1":  # This should work after fix
                return (120.128619, 23.133989)
            elif address == "5號之2":  # This should not match
                return None
            return None
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel, \
             patch.object(processor, 'query_address_coordinates', side_effect=mock_query_coordinates):
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            # Process the data
            processed_data, unmatched = processor.process_data("dummy_path.xlsx")
            
            # Verify results
            assert len(processed_data) == 3  # 3 valid addresses (1 cross-district filtered out)
            assert len(unmatched) == 1  # 1 unmatched address (5號之2)
            
            # Check that dash-to-zhi conversion worked
            wang_item = next(item for item in processed_data if item["name"] == "王明洲")
            assert wang_item["full_address"] == "七股74號之1"
            assert wang_item["longitude"] == 120.128619
            assert wang_item["latitude"] == 23.133989
            
            # Check unmatched item
            assert unmatched[0]["name"] == "黃明通"
            assert unmatched[0]["standardized_address"] == "5號之2"
            
            # Check invalid addresses were recorded
            assert hasattr(processor, 'invalid_addresses')
            assert len(processor.invalid_addresses) == 1
            assert processor.invalid_addresses[0]["name"] == "黃文騫"


class TestCrossVillageProcessing:
    """Test cases for cross-village processing functionality"""
    
    @pytest.fixture
    def processor_with_cross_village(self):
        """Create a VillageProcessor instance with cross-village enabled"""
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            return VillageProcessor("七股區", "七股里", include_cross_village=True)
    
    @pytest.fixture
    def processor_without_cross_village(self):
        """Create a VillageProcessor instance with cross-village disabled (default)"""
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            return VillageProcessor("七股區", "七股里", include_cross_village=False)
    
    def test_cross_village_parameter_initialization(self):
        """Test that include_cross_village parameter is properly initialized"""
        with patch('survey_grouping.processors.village_processor.get_supabase_client'):
            # Test default behavior (cross-village disabled)
            processor_default = VillageProcessor("七股區", "七股里")
            assert processor_default.include_cross_village is False
            
            # Test explicit False
            processor_false = VillageProcessor("七股區", "七股里", include_cross_village=False)
            assert processor_false.include_cross_village is False
            
            # Test explicit True
            processor_true = VillageProcessor("七股區", "七股里", include_cross_village=True)
            assert processor_true.include_cross_village is True
    
    def test_cross_village_address_detection_enabled(self, processor_with_cross_village):
        """Test cross-village address detection when enabled"""
        # Mock roster data with cross-village addresses
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "本里住戶", "臺南市七股區七股里13鄰七股123號"],
            [2, "臺南市七股區七股里", "跨村里住戶", "臺南市七股區塩埕里6鄰鹽埕237號之3"],
            [3, "臺南市七股區七股里", "跨區住戶", "臺南市安南區七股116號之19"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            data = processor_with_cross_village.read_excel_data("dummy_path.xlsx")
            
            # Should process main village address
            assert len(data) == 1
            assert data[0]["name"] == "本里住戶"
            
            # Should have recorded cross-village address
            assert hasattr(processor_with_cross_village, 'cross_village_data')
            assert len(processor_with_cross_village.cross_village_data) == 1
            assert processor_with_cross_village.cross_village_data[0]["name"] == "跨村里住戶"
            assert processor_with_cross_village.cross_village_data[0]["standardized_address"] == "塩埕里鹽埕237號之3"
            
            # Should have recorded invalid (cross-district) address
            assert hasattr(processor_with_cross_village, 'invalid_addresses')
            assert len(processor_with_cross_village.invalid_addresses) == 1
            assert processor_with_cross_village.invalid_addresses[0]["name"] == "跨區住戶"
    
    def test_cross_village_address_detection_disabled(self, processor_without_cross_village):
        """Test cross-village address detection when disabled (default behavior)"""
        # Mock roster data with cross-village addresses
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [1, "臺南市七股區七股里", "本里住戶", "臺南市七股區七股里13鄰七股123號"],
            [2, "臺南市七股區七股里", "跨村里住戶", "臺南市七股區塩埕里6鄰鹽埕237號之3"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            data = processor_without_cross_village.read_excel_data("dummy_path.xlsx")
            
            # Should process main village address
            assert len(data) == 1
            assert data[0]["name"] == "本里住戶"
            
            # Should NOT have recorded cross-village address (treated as invalid)
            assert not hasattr(processor_without_cross_village, 'cross_village_data') or not processor_without_cross_village.cross_village_data
            
            # Should have recorded cross-village address as invalid
            assert hasattr(processor_without_cross_village, 'invalid_addresses')
            assert len(processor_without_cross_village.invalid_addresses) == 1
            assert processor_without_cross_village.invalid_addresses[0]["name"] == "跨村里住戶"
            assert processor_without_cross_village.invalid_addresses[0]["reason"] == "非七股區地址"
    
    def test_standardize_cross_village_address(self, processor_with_cross_village):
        """Test cross-village address standardization"""
        test_cases = [
            ("臺南市七股區塩埕里6鄰鹽埕237號之3", "塩埕里鹽埕237號之3"),
            ("臺南市七股區樹林里5鄰樹林45號", "樹林里樹林45號"),
            ("724臺南市七股區十份里9鄰85-4號", "724十份里85號之4"),
        ]
        
        for input_addr, expected in test_cases:
            result = processor_with_cross_village._standardize_cross_village_address(input_addr)
            assert result == expected, f"Failed for {input_addr}: got {result}, expected {expected}"
    
    def test_extract_village_name(self, processor_with_cross_village):
        """Test village name extraction from full address"""
        test_cases = [
            ("臺南市七股區塩埕里6鄰鹽埕237號之3", "塩埕里"),
            ("臺南市七股區樹林里5鄰樹林45號", "樹林里"),
            ("724臺南市七股區十份里9鄰85-4號", "十份里"),
            ("臺南市七股區七股里13鄰七股123號", "七股里"),
            ("無效地址格式", "七股里"),  # Should return default village
        ]
        
        for input_addr, expected in test_cases:
            result = processor_with_cross_village._extract_village_name(input_addr)
            assert result == expected, f"Failed for {input_addr}: got {result}, expected {expected}"
    
    def test_query_address_coordinates_with_target_village(self, processor_with_cross_village):
        """Test coordinate query with target village parameter"""
        # Mock successful response for cross-village query
        mock_data = [{"x_coord": 120.123456, "y_coord": 23.654321}]
        mock_response = Mock()
        mock_response.data = mock_data
        processor_with_cross_village.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        result = processor_with_cross_village.query_address_coordinates("鹽埕237號之3", "塩埕里")
        
        assert result == (120.123456, 23.654321)
        
        # Verify the query method was called
        processor_with_cross_village.supabase.table.assert_called_with("addresses")
        processor_with_cross_village.supabase.table.return_value.select.assert_called_with("x_coord, y_coord")
    
    def test_process_data_with_cross_village_enabled(self, processor_with_cross_village):
        """Test complete data processing workflow with cross-village enabled"""
        # Mock cross-village data
        processor_with_cross_village.cross_village_data = [
            {
                "serial_number": "2",
                "name": "跨村里住戶",
                "original_address": "臺南市七股區塩埕里6鄰鹽埕237號之3",
                "standardized_address": "塩埕里鹽埕237號之3",
                "neighborhood": 6,
                "sheet_name": "七股里"
            }
        ]
        
        # Mock main village data
        main_data = [
            {
                "serial_number": "1",
                "name": "本里住戶",
                "original_address": "臺南市七股區七股里13鄰七股123號",
                "neighborhood": 13
            }
        ]
        
        def mock_query_coordinates(address, target_village=None):
            if address == "七股123號" and (target_village is None or target_village == "七股里"):
                return (120.130496, 23.135225)
            elif address == "塩埕里鹽埕237號之3" and target_village == "塩埕里":
                return (120.123456, 23.654321)
            return None
        
        with patch.object(processor_with_cross_village, 'read_excel_data', return_value=main_data), \
             patch.object(processor_with_cross_village, 'query_address_coordinates', side_effect=mock_query_coordinates), \
             patch('survey_grouping.processors.village_processor.standardize_village_address', side_effect=lambda x, y: "七股123號"):
            
            processed_data, unmatched, cross_village = processor_with_cross_village.process_data("dummy_path.xlsx")
            
            # Should have 1 main village address
            assert len(processed_data) == 1
            assert processed_data[0]["name"] == "本里住戶"
            assert processed_data[0]["longitude"] == 120.130496
            
            # Should have 1 cross-village address
            assert len(cross_village) == 1
            assert cross_village[0]["name"] == "跨村里住戶"
            assert cross_village[0]["village"] == "塩埕里"
            assert cross_village[0]["longitude"] == 120.123456
            assert cross_village[0]["latitude"] == 23.654321
            
            # No unmatched addresses in this test
            assert len(unmatched) == 0
    
    def test_export_cross_village_addresses(self, processor_with_cross_village):
        """Test cross-village addresses export functionality"""
        cross_village_data = [
            {
                "serial_number": "2",
                "name": "跨村里住戶1",
                "full_address": "塩埕里鹽埕237號之3",
                "district": "七股區",
                "village": "塩埕里",
                "neighborhood": 6,
                "longitude": 120.123456,
                "latitude": 23.654321,
            },
            {
                "serial_number": "3",
                "name": "跨村里住戶2",
                "full_address": "樹林里樹林45號",
                "district": "七股區",
                "village": "樹林里",
                "neighborhood": 5,
                "longitude": None,
                "latitude": None,
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor_with_cross_village.export_cross_village_addresses(cross_village_data, tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify content
            df = pd.read_csv(tmp_path, encoding='utf-8-sig')
            assert len(df) == 2
            assert list(df.columns) == ["序號", "姓名", "完整地址", "區域", "村里", "鄰別", "經度", "緯度"]
            
            # Check first row (with coordinates)
            assert df.iloc[0]["序號"] == 2
            assert df.iloc[0]["姓名"] == "跨村里住戶1"
            assert df.iloc[0]["村里"] == "塩埕里"
            assert df.iloc[0]["經度"] == 120.123456
            
            # Check second row (without coordinates)
            assert df.iloc[1]["序號"] == 3
            assert df.iloc[1]["姓名"] == "跨村里住戶2"
            assert df.iloc[1]["村里"] == "樹林里"
            assert pd.isna(df.iloc[1]["經度"])
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_export_cross_village_addresses_empty(self, processor_with_cross_village):
        """Test cross-village addresses export with empty data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            processor_with_cross_village.export_cross_village_addresses([], tmp_path)
            
            # Should not create file for empty data
            # (based on the implementation that skips export when no cross-village addresses)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_roster_format_with_variable_columns(self, processor_with_cross_village):
        """Test roster format handling with different column counts"""
        # Test with 6 columns (like 十份里 data)
        roster_data_6_cols = pd.DataFrame([
            ["臺南市七股區十份里 名冊", None, None, None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址", "額外欄1", "額外欄2"],
            [None, None, None, None, None, None],
            [1, "臺南市七股區十份里", "測試住戶", "臺南市七股區十份里17鄰十份36號之28", "extra1", "extra2"],
        ])
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel:
            
            mock_excel_file.return_value.sheet_names = ["十份里"]
            mock_read_excel.return_value = roster_data_6_cols
            
            # Should handle 6 columns by using only first 4
            data = processor_with_cross_village.read_excel_data("dummy_path.xlsx")
            
            # Should still extract data correctly
            assert len(data) == 0  # No valid data for 七股里 processor looking at 十份里 data
            assert hasattr(processor_with_cross_village, 'cross_village_data')
            assert len(processor_with_cross_village.cross_village_data) == 1
            assert processor_with_cross_village.cross_village_data[0]["name"] == "測試住戶"
    
    def test_comprehensive_cross_village_workflow(self, processor_with_cross_village):
        """Test complete cross-village workflow with real data patterns"""
        # Mock comprehensive roster data (similar to real 七股里 data)
        roster_data = pd.DataFrame([
            ["臺南市七股區七股里 名冊", None, None, None],
            ["編號", "鄉鎮市區村里", "姓名", "通訊地址"],
            [None, None, None, None],
            [26, "臺南市七股區七股里", "曾榮裕", "臺南市七股區七股里2鄰七股22號之4"],
            [30, "臺南市七股區七股里", "黃文騫", "臺南市七股區塩埕里6鄰鹽埕237號之3"],  # Cross-village
            [33, "臺南市七股區七股里", "黃明通", "臺南市七股區七股里7鄰5-2號"],  # Incomplete address
            [34, "臺南市七股區七股里", "吳國民", "臺南市七股區七股116號之19"],  # Incomplete address
        ])
        
        def mock_query_coordinates(address, target_village=None):
            """Mock coordinate query with realistic responses"""
            if address == "七股22號之4" and (target_village is None or target_village == "七股里"):
                return (120.130981, 23.132992)
            elif address == "塩埕里鹽埕237號之3" and target_village == "塩埕里":
                return (120.123456, 23.654321)
            elif address == "5號之2":  # Incomplete address
                return None
            elif address == "七股116號之19":  # Incomplete address  
                return None
            return None
        
        with patch('pandas.ExcelFile') as mock_excel_file, \
             patch('pandas.read_excel') as mock_read_excel, \
             patch.object(processor_with_cross_village, 'query_address_coordinates', side_effect=mock_query_coordinates):
            
            mock_excel_file.return_value.sheet_names = ["七股里"]
            mock_read_excel.return_value = roster_data
            
            # Process the data
            processed_data, unmatched, cross_village = processor_with_cross_village.process_data("dummy_path.xlsx")
            
            # Verify main village results
            assert len(processed_data) == 2  # 1 valid + 1 unmatched main village addresses
            matched_main = [item for item in processed_data if item["longitude"] is not None]
            unmatched_main = [item for item in processed_data if item["longitude"] is None]
            assert len(matched_main) == 1
            assert len(unmatched_main) == 1
            assert matched_main[0]["name"] == "曾榮裕"
            assert unmatched_main[0]["name"] == "黃明通"
            
            # Verify cross-village results (should include both 黃文騫 and 吳國民)
            assert len(cross_village) == 2
            cross_village_names = [item["name"] for item in cross_village]
            assert "黃文騫" in cross_village_names
            assert "吳國民" in cross_village_names
            
            # Find the specific cross-village items
            huang_item = next(item for item in cross_village if item["name"] == "黃文騫")
            wu_item = next(item for item in cross_village if item["name"] == "吳國民")
            
            assert huang_item["village"] == "塩埕里"
            assert huang_item["longitude"] == 120.123456
            assert wu_item["longitude"] is None  # Should not match coordinates
            
            # Verify unmatched list
            assert len(unmatched) == 1
            assert unmatched[0]["name"] == "黃明通"
            
            # Verify invalid addresses (should be empty as both cross-district addresses are now cross-village)
            assert not hasattr(processor_with_cross_village, 'invalid_addresses') or len(processor_with_cross_village.invalid_addresses) == 0