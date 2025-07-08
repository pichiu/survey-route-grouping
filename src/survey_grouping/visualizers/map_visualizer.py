"""地圖視覺化器

主要的地圖視覺化類別，整合 Folium 渲染器和顏色配置。
"""

from typing import List, Optional
from pathlib import Path

from ..models.group import RouteGroup
from .folium_renderer import FoliumRenderer


class MapVisualizer:
    """地圖視覺化器"""

    def __init__(self):
        self.renderer = FoliumRenderer()

    def create_overview_map(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_path: str,
    ) -> bool:
        """建立總覽地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_path: 輸出檔案路徑
            
        Returns:
            是否成功建立
        """
        try:
            # 建立地圖
            map_obj = self.renderer.create_overview_map(
                groups, district, village
            )
            
            # 確保輸出目錄存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 儲存地圖
            map_obj.save(str(output_file))
            
            return True
            
        except Exception as e:
            print(f"建立總覽地圖失敗: {e}")
            return False

    def create_group_maps(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_dir: str,
    ) -> List[str]:
        """建立個別分組地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_dir: 輸出目錄
            
        Returns:
            成功建立的檔案路徑列表
        """
        created_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, group in enumerate(groups):
            try:
                # 建立地圖
                map_obj = self.renderer.create_group_map(
                    group, i, district, village
                )
                
                # 生成檔案名稱
                filename = f"{district}{village}_第{i+1}組.html"
                file_path = output_path / filename
                
                # 儲存地圖
                map_obj.save(str(file_path))
                created_files.append(str(file_path))
                
            except Exception as e:
                print(f"建立分組地圖 {group.group_id} 失敗: {e}")
                continue

        return created_files

    def create_all_maps(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        output_dir: str,
        overview_only: bool = False,
        groups_only: bool = False,
    ) -> dict:
        """建立所有地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            output_dir: 輸出目錄
            overview_only: 只建立總覽地圖
            groups_only: 只建立分組地圖
            
        Returns:
            建立結果字典
        """
        result = {
            "overview_map": None,
            "group_maps": [],
            "success": True,
            "errors": [],
        }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 建立總覽地圖
        if not groups_only:
            overview_file = output_path / f"{district}{village}_總覽.html"
            if self.create_overview_map(groups, district, village, str(overview_file)):
                result["overview_map"] = str(overview_file)
            else:
                result["errors"].append("總覽地圖建立失敗")
                result["success"] = False

        # 建立分組地圖
        if not overview_only:
            group_files = self.create_group_maps(groups, district, village, output_dir)
            result["group_maps"] = group_files
            
            if len(group_files) != len(groups):
                result["errors"].append(
                    f"部分分組地圖建立失敗 ({len(group_files)}/{len(groups)})"
                )
                result["success"] = False

        return result

    def get_map_summary(self, groups: List[RouteGroup]) -> dict:
        """取得地圖摘要資訊
        
        Args:
            groups: 分組列表
            
        Returns:
            摘要資訊字典
        """
        total_addresses = sum(group.size for group in groups)
        total_distance = sum(group.estimated_distance or 0 for group in groups)
        total_time = sum(group.estimated_time or 0 for group in groups)

        # 計算地理範圍
        all_coords = []
        for group in groups:
            for addr in group.addresses:
                if addr.has_valid_coordinates:
                    all_coords.append((addr.y_coord, addr.x_coord))

        bounds = None
        center = None
        if all_coords:
            lats = [coord[0] for coord in all_coords]
            lngs = [coord[1] for coord in all_coords]
            
            bounds = {
                "min_lat": min(lats),
                "max_lat": max(lats),
                "min_lng": min(lngs),
                "max_lng": max(lngs),
            }
            
            center = {
                "lat": sum(lats) / len(lats),
                "lng": sum(lngs) / len(lngs),
            }

        return {
            "total_groups": len(groups),
            "total_addresses": total_addresses,
            "avg_group_size": total_addresses / len(groups) if groups else 0,
            "total_distance": total_distance,
            "total_time": total_time,
            "geographic_bounds": bounds,
            "geographic_center": center,
            "group_details": [
                {
                    "group_id": group.group_id,
                    "size": group.size,
                    "estimated_distance": group.estimated_distance,
                    "estimated_time": group.estimated_time,
                    "neighborhood_distribution": group.address_count_by_neighborhood,
                }
                for group in groups
            ],
        }
