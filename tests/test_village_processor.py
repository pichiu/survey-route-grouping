"""
Tests for VillageProcessor
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import tempfile
import os

from survey_grouping.processors.village_processor import VillageProcessor


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