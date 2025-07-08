"""Folium 渲染器

使用 Folium 生成互動式地圖的核心渲染器。
"""

from typing import List, Dict, Any, Optional, Tuple
import folium
from folium import plugins
import branca.colormap as cm

from ..models.group import RouteGroup
from ..models.address import Address
from .color_schemes import ColorScheme


class FoliumRenderer:
    """Folium 地圖渲染器"""

    def __init__(self):
        self.color_scheme = ColorScheme()

    def create_overview_map(
        self,
        groups: List[RouteGroup],
        district: str,
        village: str,
        center_coords: Optional[Tuple[float, float]] = None,
    ) -> folium.Map:
        """建立總覽地圖
        
        Args:
            groups: 分組列表
            district: 行政區名稱
            village: 村里名稱
            center_coords: 地圖中心座標 (lat, lng)
            
        Returns:
            Folium 地圖物件
        """
        # 計算地圖中心點
        if not center_coords:
            center_coords = self._calculate_center(groups)

        # 建立地圖
        m = folium.Map(
            location=center_coords,
            zoom_start=15,
            tiles="OpenStreetMap",
        )

        # 添加標題
        title_html = f"""
        <h3 align="center" style="font-size:20px">
            <b>{district}{village} 普查路線分組總覽</b>
        </h3>
        """
        m.get_root().html.add_child(folium.Element(title_html))

        # 建立圖層控制
        feature_groups = {}
        
        # 為每個分組建立圖層
        for i, group in enumerate(groups):
            group_name = f"{group.group_id} ({group.size}個地址)"
            fg = folium.FeatureGroup(name=group_name)
            
            # 添加標記
            self._add_group_markers(fg, group, i)
            
            # 添加路線
            if len(group.addresses) > 1:
                self._add_route_line(fg, group, i)
            
            feature_groups[group.group_id] = fg
            m.add_child(fg)

        # 添加圖層控制
        folium.LayerControl().add_to(m)

        # 添加統計資訊
        self._add_statistics_panel(m, groups, district, village)

        # 添加圖例
        self._add_legend(m, groups)

        return m

    def create_group_map(
        self,
        group: RouteGroup,
        group_index: int,
        district: str,
        village: str,
    ) -> folium.Map:
        """建立單一分組地圖
        
        Args:
            group: 分組物件
            group_index: 分組索引
            district: 行政區名稱
            village: 村里名稱
            
        Returns:
            Folium 地圖物件
        """
        # 計算地圖中心點
        center_coords = self._calculate_group_center(group)

        # 建立地圖
        m = folium.Map(
            location=center_coords,
            zoom_start=16,
            tiles="OpenStreetMap",
        )

        # 添加標題
        title_html = f"""
        <h3 align="center" style="font-size:18px">
            <b>{group.group_id} 詳細路線</b><br>
            <span style="font-size:14px">
                {group.size} 個地址 | 
                預估距離: {group.estimated_distance or 0:.0f}m | 
                預估時間: {group.estimated_time or 0} 分鐘
            </span>
        </h3>
        """
        m.get_root().html.add_child(folium.Element(title_html))

        # 添加標記（帶訪問順序）
        self._add_ordered_markers(m, group, group_index)

        # 添加路線
        if len(group.addresses) > 1:
            self._add_detailed_route(m, group, group_index)

        # 添加分組統計
        self._add_group_statistics(m, group)

        return m

    def _calculate_center(self, groups: List[RouteGroup]) -> Tuple[float, float]:
        """計算所有分組的地理中心點"""
        all_coords = []
        for group in groups:
            for addr in group.addresses:
                if addr.has_valid_coordinates:
                    all_coords.append((addr.y_coord, addr.x_coord))  # (lat, lng)

        if not all_coords:
            return (23.0, 120.0)  # 台灣中心點

        avg_lat = sum(coord[0] for coord in all_coords) / len(all_coords)
        avg_lng = sum(coord[1] for coord in all_coords) / len(all_coords)
        
        return (avg_lat, avg_lng)

    def _calculate_group_center(self, group: RouteGroup) -> Tuple[float, float]:
        """計算單一分組的地理中心點"""
        valid_coords = [
            (addr.y_coord, addr.x_coord)
            for addr in group.addresses
            if addr.has_valid_coordinates
        ]

        if not valid_coords:
            return (23.0, 120.0)

        avg_lat = sum(coord[0] for coord in valid_coords) / len(valid_coords)
        avg_lng = sum(coord[1] for coord in valid_coords) / len(valid_coords)
        
        return (avg_lat, avg_lng)

    def _add_group_markers(
        self, 
        feature_group: folium.FeatureGroup, 
        group: RouteGroup, 
        group_index: int
    ):
        """添加分組標記"""
        marker_color = self.color_scheme.get_marker_color(group_index)
        
        for addr in group.addresses:
            if not addr.has_valid_coordinates:
                continue

            # 建立彈出視窗內容
            popup_html = f"""
            <div style="width: 200px;">
                <h4>{group.group_id}</h4>
                <p><strong>地址:</strong> {addr.full_address}</p>
                <p><strong>鄰別:</strong> {addr.neighborhood}鄰</p>
                <p><strong>座標:</strong> {addr.y_coord:.6f}, {addr.x_coord:.6f}</p>
            </div>
            """

            folium.Marker(
                location=[addr.y_coord, addr.x_coord],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=addr.full_address,
                icon=folium.Icon(color=marker_color, icon="home"),
            ).add_to(feature_group)

    def _add_ordered_markers(
        self, 
        map_obj: folium.Map, 
        group: RouteGroup, 
        group_index: int
    ):
        """添加帶訪問順序的標記"""
        marker_color = self.color_scheme.get_marker_color(group_index)
        
        # 建立地址字典
        addr_dict = {addr.id: addr for addr in group.addresses}
        
        # 按路線順序添加標記
        route_order = group.route_order or [addr.id for addr in group.addresses]
        
        for order, addr_id in enumerate(route_order, 1):
            addr = addr_dict.get(addr_id)
            if not addr or not addr.has_valid_coordinates:
                continue

            # 建立彈出視窗內容
            popup_html = f"""
            <div style="width: 220px;">
                <h4>訪問順序: {order}</h4>
                <p><strong>地址:</strong> {addr.full_address}</p>
                <p><strong>鄰別:</strong> {addr.neighborhood}鄰</p>
                <p><strong>座標:</strong> {addr.y_coord:.6f}, {addr.x_coord:.6f}</p>
            </div>
            """

            # 使用 DivIcon 顯示順序編號
            folium.Marker(
                location=[addr.y_coord, addr.x_coord],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{order}. {addr.full_address}",
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                        background-color: {self.color_scheme.get_group_color(group_index)};
                        border: 2px solid white;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 14px;
                        color: white;
                        text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
                    ">{order}</div>
                    """,
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                ),
            ).add_to(map_obj)

    def _add_route_line(
        self, 
        feature_group: folium.FeatureGroup, 
        group: RouteGroup, 
        group_index: int
    ):
        """添加路線連線"""
        if len(group.addresses) < 2:
            return

        # 建立地址字典
        addr_dict = {addr.id: addr for addr in group.addresses}
        
        # 按路線順序建立座標列表
        route_coords = []
        route_order = group.route_order or [addr.id for addr in group.addresses]
        
        for addr_id in route_order:
            addr = addr_dict.get(addr_id)
            if addr and addr.has_valid_coordinates:
                route_coords.append([addr.y_coord, addr.x_coord])

        if len(route_coords) < 2:
            return

        # 添加路線
        folium.PolyLine(
            locations=route_coords,
            color=self.color_scheme.get_group_color(group_index),
            weight=3,
            opacity=0.8,
            popup=f"{group.group_id} 路線",
        ).add_to(feature_group)

    def _add_detailed_route(
        self, 
        map_obj: folium.Map, 
        group: RouteGroup, 
        group_index: int
    ):
        """添加詳細路線（帶箭頭）"""
        if len(group.addresses) < 2:
            return

        # 建立地址字典
        addr_dict = {addr.id: addr for addr in group.addresses}
        
        # 按路線順序建立座標列表
        route_coords = []
        route_order = group.route_order or [addr.id for addr in group.addresses]
        
        for addr_id in route_order:
            addr = addr_dict.get(addr_id)
            if addr and addr.has_valid_coordinates:
                route_coords.append([addr.y_coord, addr.x_coord])

        if len(route_coords) < 2:
            return

        # 添加路線
        folium.PolyLine(
            locations=route_coords,
            color=self.color_scheme.get_group_color(group_index),
            weight=4,
            opacity=0.9,
        ).add_to(map_obj)

        # 添加方向箭頭
        plugins.PolyLineTextPath(
            folium.PolyLine(route_coords, weight=0),
            "►",
            repeat=True,
            offset=7,
            attributes={
                "fill": self.color_scheme.get_group_color(group_index),
                "font-weight": "bold",
                "font-size": "20",
            },
        ).add_to(map_obj)

    def _add_statistics_panel(
        self, 
        map_obj: folium.Map, 
        groups: List[RouteGroup], 
        district: str, 
        village: str
    ):
        """添加統計資訊面板"""
        total_addresses = sum(group.size for group in groups)
        total_distance = sum(
            group.estimated_distance or 0 for group in groups
        )
        total_time = sum(group.estimated_time or 0 for group in groups)

        stats_html = f"""
        <div style="
            position: fixed;
            top: 10px;
            right: 10px;
            width: 250px;
            background: white;
            border: 2px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 9999;
        ">
            <h4 style="margin: 0 0 10px 0;">{district}{village} 統計</h4>
            <p><strong>總分組數:</strong> {len(groups)} 組</p>
            <p><strong>總地址數:</strong> {total_addresses} 個</p>
            <p><strong>平均組大小:</strong> {total_addresses/len(groups):.1f} 個</p>
            <p><strong>總預估距離:</strong> {total_distance:.0f} 公尺</p>
            <p><strong>總預估時間:</strong> {total_time} 分鐘</p>
        </div>
        """
        
        map_obj.get_root().html.add_child(folium.Element(stats_html))

    def _add_group_statistics(self, map_obj: folium.Map, group: RouteGroup):
        """添加分組統計資訊"""
        neighborhood_dist = group.address_count_by_neighborhood

        stats_html = f"""
        <div style="
            position: fixed;
            top: 10px;
            right: 10px;
            width: 200px;
            background: white;
            border: 2px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 9999;
        ">
            <h4 style="margin: 0 0 10px 0;">分組統計</h4>
            <p><strong>地址數量:</strong> {group.size} 個</p>
            <p><strong>預估距離:</strong> {group.estimated_distance or 0:.0f} 公尺</p>
            <p><strong>預估時間:</strong> {group.estimated_time or 0} 分鐘</p>
            <p><strong>鄰別分布:</strong></p>
            <ul style="margin: 5px 0; padding-left: 20px;">
        """
        
        for neighborhood, count in neighborhood_dist.items():
            stats_html += f"<li>{neighborhood}鄰: {count}個</li>"
        
        stats_html += """
            </ul>
        </div>
        """
        
        map_obj.get_root().html.add_child(folium.Element(stats_html))

    def _add_legend(self, map_obj: folium.Map, groups: List[RouteGroup]):
        """添加圖例"""
        legend_html = """
        <div style="
            position: fixed;
            bottom: 50px;
            left: 10px;
            width: 200px;
            background: white;
            border: 2px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 9999;
        ">
            <h4 style="margin: 0 0 10px 0;">圖例</h4>
        """
        
        for i, group in enumerate(groups):
            color = self.color_scheme.get_group_color(i)
            legend_html += f"""
            <p style="margin: 5px 0;">
                <span style="
                    display: inline-block;
                    width: 15px;
                    height: 15px;
                    background-color: {color};
                    border: 1px solid #000;
                    margin-right: 5px;
                "></span>
                {group.group_id} ({group.size}個)
            </p>
            """
        
        legend_html += "</div>"
        
        map_obj.get_root().html.add_child(folium.Element(legend_html))
