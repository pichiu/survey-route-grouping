"""視覺化模組測試

測試地圖視覺化、顏色配置等功能。
"""

import pytest
from pathlib import Path
from survey_grouping.visualizers.color_schemes import ColorScheme
from survey_grouping.visualizers.map_visualizer import MapVisualizer
from survey_grouping.visualizers.folium_renderer import FoliumRenderer
from survey_grouping.exporters.map_exporter import MapExporter


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
        from survey_grouping.models.group import RouteGroup
        
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
        from survey_grouping.models.group import RouteGroup
        
        groups = [RouteGroup(group_id="G001", addresses=sample_addresses)]
        renderer = FoliumRenderer()
        
        center = renderer._calculate_center(groups)
        
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert isinstance(center[0], float)
        assert isinstance(center[1], float)

    def test_calculate_group_center(self, sample_addresses):
        """測試計算分組中心點"""
        from survey_grouping.models.group import RouteGroup
        
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
        from survey_grouping.models.group import RouteGroup
        
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
        from survey_grouping.models.group import RouteGroup
        
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
        from survey_grouping.models.address import Address
        from survey_grouping.models.group import RouteGroup
        
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
