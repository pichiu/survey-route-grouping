"""地圖匯出器

提供地圖視覺化的匯出功能。
"""

from typing import List
from pathlib import Path

from ..models.group import RouteGroup, GroupingResult
from ..visualizers.map_visualizer import MapVisualizer


class MapExporter:
    """地圖匯出器"""

    def __init__(self):
        self.visualizer = MapVisualizer()

    def export_overview_map(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_path: str,
    ) -> bool:
        """匯出總覽地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_path: 輸出檔案路徑
            
        Returns:
            是否成功匯出
        """
        return self.visualizer.create_overview_map(
            groups, district, village, output_path
        )

    def export_group_maps(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_dir: str,
    ) -> List[str]:
        """匯出個別分組地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_dir: 輸出目錄
            
        Returns:
            成功匯出的檔案路徑列表
        """
        return self.visualizer.create_group_maps(
            groups, district, village, output_dir
        )

    def export_all_maps(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_dir: str,
        overview_only: bool = False,
        groups_only: bool = False,
    ) -> dict:
        """匯出所有地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_dir: 輸出目錄
            overview_only: 只匯出總覽地圖
            groups_only: 只匯出分組地圖
            
        Returns:
            匯出結果字典
        """
        return self.visualizer.create_all_maps(
            groups, district, village, output_dir, overview_only, groups_only
        )

    def export_grouping_result_maps(
        self,
        result: GroupingResult,
        output_dir: str,
        overview_only: bool = False,
        groups_only: bool = False,
    ) -> dict:
        """匯出分組結果的地圖
        
        Args:
            result: 分組結果
            output_dir: 輸出目錄
            overview_only: 只匯出總覽地圖
            groups_only: 只匯出分組地圖
            
        Returns:
            匯出結果字典
        """
        return self.export_all_maps(
            result.groups,
            result.district,
            result.village,
            output_dir,
            overview_only,
            groups_only,
        )

    def get_export_summary(self, groups: List[RouteGroup]) -> dict:
        """取得匯出摘要
        
        Args:
            groups: 分組列表
            
        Returns:
            匯出摘要字典
        """
        return self.visualizer.get_map_summary(groups)
