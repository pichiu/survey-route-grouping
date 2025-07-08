"""顏色配置模組

提供地圖視覺化的顏色方案和配置。
"""

from typing import List, Dict, Any
import colorsys


class ColorScheme:
    """顏色配置類別"""

    # 預定義的顏色方案
    DISTINCT_COLORS = [
        "#FF6B6B",  # 紅色
        "#4ECDC4",  # 青色
        "#45B7D1",  # 藍色
        "#96CEB4",  # 綠色
        "#FFEAA7",  # 黃色
        "#DDA0DD",  # 紫色
        "#98D8C8",  # 薄荷綠
        "#F7DC6F",  # 金黃色
        "#BB8FCE",  # 淡紫色
        "#85C1E9",  # 天藍色
        "#F8C471",  # 橙色
        "#82E0AA",  # 淺綠色
        "#F1948A",  # 粉紅色
        "#85C1E9",  # 淺藍色
        "#D7BDE2",  # 淡紫色
    ]

    MARKER_COLORS = [
        "red",
        "blue", 
        "green",
        "purple",
        "orange",
        "darkred",
        "lightred",
        "beige",
        "darkblue",
        "darkgreen",
        "cadetblue",
        "darkpurple",
        "white",
        "pink",
        "lightblue",
        "lightgreen",
        "gray",
        "black",
        "lightgray",
    ]

    @classmethod
    def get_group_color(cls, group_index: int) -> str:
        """取得分組顏色
        
        Args:
            group_index: 分組索引（從 0 開始）
            
        Returns:
            顏色代碼
        """
        return cls.DISTINCT_COLORS[group_index % len(cls.DISTINCT_COLORS)]

    @classmethod
    def get_marker_color(cls, group_index: int) -> str:
        """取得標記顏色
        
        Args:
            group_index: 分組索引（從 0 開始）
            
        Returns:
            Folium 標記顏色名稱
        """
        return cls.MARKER_COLORS[group_index % len(cls.MARKER_COLORS)]

    @classmethod
    def generate_colors(cls, num_colors: int) -> List[str]:
        """生成指定數量的不同顏色
        
        Args:
            num_colors: 需要的顏色數量
            
        Returns:
            顏色代碼列表
        """
        if num_colors <= len(cls.DISTINCT_COLORS):
            return cls.DISTINCT_COLORS[:num_colors]
        
        # 如果需要更多顏色，使用 HSV 色彩空間生成
        colors = cls.DISTINCT_COLORS.copy()
        
        for i in range(len(cls.DISTINCT_COLORS), num_colors):
            # 使用黃金角度分割來生成均勻分布的色相
            hue = (i * 137.508) % 360  # 黃金角度 ≈ 137.508°
            saturation = 0.7 + (i % 3) * 0.1  # 0.7, 0.8, 0.9
            value = 0.8 + (i % 2) * 0.1  # 0.8, 0.9
            
            rgb = colorsys.hsv_to_rgb(hue / 360, saturation, value)
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255)
            )
            colors.append(hex_color)
        
        return colors

    @classmethod
    def get_color_palette(cls, num_groups: int) -> Dict[str, Any]:
        """取得完整的顏色調色盤
        
        Args:
            num_groups: 分組數量
            
        Returns:
            包含各種顏色配置的字典
        """
        return {
            "fill_colors": cls.generate_colors(num_groups),
            "marker_colors": [
                cls.get_marker_color(i) for i in range(num_groups)
            ],
            "line_colors": cls.generate_colors(num_groups),
        }

    @classmethod
    def get_route_color(cls, group_index: int, alpha: float = 0.8) -> str:
        """取得路線顏色（帶透明度）
        
        Args:
            group_index: 分組索引
            alpha: 透明度 (0-1)
            
        Returns:
            RGBA 顏色字串
        """
        base_color = cls.get_group_color(group_index)
        # 將 hex 轉換為 RGB
        hex_color = base_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"

    @classmethod
    def get_legend_style(cls) -> Dict[str, str]:
        """取得圖例樣式
        
        Returns:
            CSS 樣式字典
        """
        return {
            "background-color": "white",
            "border": "2px solid grey",
            "border-radius": "5px",
            "padding": "10px",
            "font-size": "14px",
            "font-family": "Arial, sans-serif",
        }
