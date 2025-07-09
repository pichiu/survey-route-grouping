"""視覺化模組測試

測試地圖視覺化、顏色配置等功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.survey_grouping.visualizers.color_schemes import ColorScheme
from src.survey_grouping.visualizers.map_visualizer import MapVisualizer
from src.survey_grouping.visualizers.folium_renderer import FoliumRenderer
from src.survey_grouping.exporters.map_exporter import MapExporter
from src.survey_grouping.models.group import RouteGroup
from src.survey_grouping.models.address import Address


class TestColorScheme:
    """顏色配置測試"""

    def test_get_group_color(self):
        """測試取得分組顏色"""
        color1 = ColorScheme.get_group_color(0)
        color2 = ColorScheme.get_group_color(1)
        
        assert color1 != color2
        assert color1.startswith("#")
        assert len(color1) == 7

    def test_get_marker_color(self):
        """測試取得標記顏色"""
        marker1 = ColorScheme.get_marker_color(0)
        marker2 = ColorScheme.get_marker_color(1)
        
        assert marker1 != marker2
        assert isinstance(marker1, str)
        assert isinstance(marker2, str)

    def test_generate_colors(self):
        """測試生成顏色"""
        colors = ColorScheme.generate_colors(5)
        
        assert len(colors) == 5
        assert all(color.startswith("#") for color in colors)
        assert len(set(colors)) == 5  # 所有顏色都不同

    def test_generate_many_colors(self):
        """測試生成大量顏色"""
        colors = ColorScheme.generate_colors(20)
        
        assert len(colors) == 20
        assert all(color.startswith("#") for color in colors)

    def test_get_color_palette(self):
        """測試取得顏色調色盤"""
        palette = ColorScheme.get_color_palette(3)
        
        assert "fill_colors" in palette
        assert "marker_colors" in palette
        assert "line_colors" in palette
        assert len(palette["fill_colors"]) == 3
        assert len(palette["marker_colors"]) == 3
        assert len(palette["line_colors"]) == 3

    def test_get_route_color(self):
        """測試取得路線顏色"""
        route_color = ColorScheme.get_route_color(0)
        
        assert route_color.startswith("rgba(")
        assert route_color.endswith(")")

    def test_get_legend_style(self):
        """測試取得圖例樣式"""
        style = ColorScheme.get_legend_style()
        
        assert isinstance(style, dict)
        assert "background-color" in style
        assert "border" in style


class TestMapVisualizer:
    """地圖視覺化器測試"""

    def test_map_visualizer_creation(self):
        """測試地圖視覺化器建立"""
        visualizer = MapVisualizer()
        assert visualizer.renderer is not None

    def test_get_map_summary(self, sample_addresses):
        """測試取得地圖摘要"""
        
        groups = [
            RouteGroup(
                group_id="G001",
                addresses=sample_addresses[:3],
                estimated_distance=500.0,
                estimated_time=30,
            ),
            RouteGroup(
                group_id="G002", 
                addresses=sample_addresses[3:],
                estimated_distance=300.0,
                estimated_time=20,
            )
        ]
        
        visualizer = MapVisualizer()
        summary = visualizer.get_map_summary(groups)
        
        assert "total_groups" in summary
        assert "total_addresses" in summary
        assert "avg_group_size" in summary
        assert "total_distance" in summary
        assert "total_time" in summary
        assert "geographic_bounds" in summary
        assert "geographic_center" in summary
        assert "group_details" in summary
        
        assert summary["total_groups"] == 2
        assert summary["total_addresses"] == len(sample_addresses)
        assert summary["total_distance"] == 800.0
        assert summary["total_time"] == 50


class TestFoliumRenderer:
    """Folium 渲染器測試"""

    def test_folium_renderer_creation(self):
        """測試 Folium 渲染器建立"""
        renderer = FoliumRenderer()
        assert renderer.color_scheme is not None

    def test_calculate_center(self, sample_addresses):
        """測試計算中心點"""
        
        groups = [RouteGroup(group_id="G001", addresses=sample_addresses)]
        renderer = FoliumRenderer()
        
        center = renderer._calculate_center(groups)
        
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert isinstance(center[0], float)
        assert isinstance(center[1], float)

    def test_calculate_group_center(self, sample_addresses):
        """測試計算分組中心點"""
        
        group = RouteGroup(group_id="G001", addresses=sample_addresses[:3])
        renderer = FoliumRenderer()
        
        center = renderer._calculate_group_center(group)
        
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert isinstance(center[0], float)
        assert isinstance(center[1], float)


class TestMapExporter:
    """地圖匯出器測試"""

    def test_map_exporter_creation(self):
        """測試地圖匯出器建立"""
        exporter = MapExporter()
        assert exporter.visualizer is not None

    def test_get_export_summary(self, sample_addresses):
        """測試取得匯出摘要"""
        
        groups = [
            RouteGroup(
                group_id="G001",
                addresses=sample_addresses[:3],
                estimated_distance=500.0,
                estimated_time=30,
            )
        ]
        
        exporter = MapExporter()
        summary = exporter.get_export_summary(groups)
        
        assert "total_groups" in summary
        assert "total_addresses" in summary
        assert summary["total_groups"] == 1
        assert summary["total_addresses"] == 3


class TestVisualizationIntegration:
    """視覺化整合測試"""

    def test_color_consistency(self):
        """測試顏色一致性"""
        # 同一個索引應該總是返回相同的顏色
        color1 = ColorScheme.get_group_color(0)
        color2 = ColorScheme.get_group_color(0)
        
        assert color1 == color2

    def test_visualization_pipeline(self, sample_addresses, tmp_path):
        """測試視覺化流程"""
        
        # 建立測試分組
        groups = [
            RouteGroup(
                group_id="G001",
                addresses=sample_addresses[:3],
                estimated_distance=500.0,
                estimated_time=30,
            )
        ]
        
        # 測試地圖視覺化器
        visualizer = MapVisualizer()
        summary = visualizer.get_map_summary(groups)
        
        assert summary["total_groups"] == 1
        assert summary["total_addresses"] == 3

    def test_error_handling_empty_groups(self):
        """測試空分組的錯誤處理"""
        visualizer = MapVisualizer()
        summary = visualizer.get_map_summary([])
        
        assert summary["total_groups"] == 0
        assert summary["total_addresses"] == 0
        assert summary["avg_group_size"] == 0

    def test_error_handling_no_coordinates(self):
        """測試無座標地址的錯誤處理"""
        
        # 建立無座標的地址
        addresses_no_coords = [
            Address(
                id=1,
                district="測試區",
                village="測試里",
                neighborhood=1,
                x_coord=None,
                y_coord=None,
                full_address="測試地址",
            )
        ]
        
        groups = [RouteGroup(group_id="G001", addresses=addresses_no_coords)]
        
        visualizer = MapVisualizer()
        summary = visualizer.get_map_summary(groups)
        
        assert summary["geographic_bounds"] is None
        assert summary["geographic_center"] is None


# 新增的 CSV 導入和視覺化邏輯測試
class TestFoliumRendererCSVSupport:
    """測試 Folium 渲染器對 CSV 導入的支援"""
    
    @pytest.fixture
    def addresses_with_coords(self):
        """提供有座標的地址資料"""
        return [
            Address(
                id=1, district='七股區', village='西寮里', neighborhood=1,
                full_address='西寮1號', x_coord=120.096955, y_coord=23.169737
            ),
            Address(
                id=2, district='七股區', village='西寮里', neighborhood=1,
                full_address='西寮2號', x_coord=120.096739, y_coord=23.169929
            )
        ]
    
    @pytest.fixture
    def group_with_route_order(self, addresses_with_coords):
        """有訪問順序的分組"""
        return RouteGroup(
            group_id='七股區西寮里-01',
            addresses=addresses_with_coords,
            route_order=[1, 2],  # 有順序
            estimated_distance=500.0,
            estimated_time=30
        )
    
    @pytest.fixture
    def group_without_route_order(self, addresses_with_coords):
        """沒有訪問順序的分組"""
        return RouteGroup(
            group_id='七股區西寮里-02',
            addresses=addresses_with_coords,
            route_order=[],  # 空的順序
            estimated_distance=None,
            estimated_time=None
        )
    
    def test_add_route_line_with_order(self, group_with_route_order):
        """測試有順序時添加路線"""
        renderer = FoliumRenderer()
        mock_feature_group = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            mock_polyline = Mock()
            mock_folium.PolyLine.return_value = mock_polyline
            
            renderer._add_route_line(mock_feature_group, group_with_route_order, 0)
            
            # 檢查有建立路線
            mock_folium.PolyLine.assert_called_once()
            mock_polyline.add_to.assert_called_once_with(mock_feature_group)
    
    def test_add_route_line_without_order(self, group_without_route_order):
        """測試沒有順序時不添加路線"""
        renderer = FoliumRenderer()
        mock_feature_group = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            renderer._add_route_line(mock_feature_group, group_without_route_order, 0)
            
            # 檢查沒有建立路線
            mock_folium.PolyLine.assert_not_called()
    
    def test_add_detailed_route_with_order(self, group_with_route_order):
        """測試有順序時添加詳細路線"""
        renderer = FoliumRenderer()
        mock_map = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            with patch('src.survey_grouping.visualizers.folium_renderer.plugins') as mock_plugins:
                renderer._add_detailed_route(mock_map, group_with_route_order, 0)
                
                # 檢查有建立路線和箭頭
                mock_folium.PolyLine.assert_called()
                mock_plugins.PolyLineTextPath.assert_called()
    
    def test_add_detailed_route_without_order(self, group_without_route_order):
        """測試沒有順序時不添加詳細路線"""
        renderer = FoliumRenderer()
        mock_map = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            with patch('src.survey_grouping.visualizers.folium_renderer.plugins') as mock_plugins:
                renderer._add_detailed_route(mock_map, group_without_route_order, 0)
                
                # 檢查沒有建立路線元素
                mock_folium.PolyLine.assert_not_called()
                mock_plugins.PolyLineTextPath.assert_not_called()
    
    def test_add_ordered_markers_with_order(self, group_with_route_order):
        """測試有順序時添加順序標記"""
        renderer = FoliumRenderer()
        mock_map = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            mock_marker = Mock()
            mock_folium.Marker.return_value = mock_marker
            mock_folium.DivIcon.return_value = Mock()
            mock_folium.Popup.return_value = Mock()
            
            renderer._add_ordered_markers(mock_map, group_with_route_order, 0)
            
            # 檢查使用 DivIcon（順序編號標記）
            mock_folium.DivIcon.assert_called()
            assert mock_marker.add_to.call_count == 2
    
    def test_add_ordered_markers_without_order(self, group_without_route_order):
        """測試沒有順序時添加一般標記"""
        renderer = FoliumRenderer()
        mock_map = Mock()
        
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            mock_marker = Mock()
            mock_folium.Marker.return_value = mock_marker
            mock_folium.Icon.return_value = Mock()
            mock_folium.Popup.return_value = Mock()
            
            renderer._add_ordered_markers(mock_map, group_without_route_order, 0)
            
            # 檢查使用一般 Icon（不是 DivIcon）
            mock_folium.Icon.assert_called()
            mock_folium.DivIcon.assert_not_called()
            assert mock_marker.add_to.call_count == 2
    
    def test_visualization_logic_consistency(self, group_with_route_order, group_without_route_order):
        """測試視覺化邏輯的一致性"""
        renderer = FoliumRenderer()
        
        # 測試有順序的分組
        with patch('src.survey_grouping.visualizers.folium_renderer.folium'):
            mock_fg = Mock()
            mock_map = Mock()
            
            # 應該添加路線
            renderer._add_route_line(mock_fg, group_with_route_order, 0)
            renderer._add_detailed_route(mock_map, group_with_route_order, 0)
        
        # 測試沒有順序的分組
        with patch('src.survey_grouping.visualizers.folium_renderer.folium') as mock_folium:
            mock_fg = Mock()
            mock_map = Mock()
            
            # 不應該添加路線
            renderer._add_route_line(mock_fg, group_without_route_order, 0)
            renderer._add_detailed_route(mock_map, group_without_route_order, 0)
            
            # 檢查沒有呼叫 PolyLine
            mock_folium.PolyLine.assert_not_called()
