"""CSV 匯出器

提供將分組結果匯出為 CSV 格式的功能。
"""

import csv
from pathlib import Path
from typing import List, Optional
from survey_grouping.models.group import RouteGroup, GroupingResult


class CSVExporter:
    """CSV 匯出器"""

    @staticmethod
    def export_groups(
        groups: List[RouteGroup], output_path: str, include_route_order: bool = True
    ) -> bool:
        """匯出分組到 CSV 檔案

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑
            include_route_order: 是否包含路線順序

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "分組編號",
                    "地址ID",
                    "完整地址",
                    "區域",
                    "村里",
                    "鄰別",
                    "街道",
                    "區段",
                    "巷",
                    "弄",
                    "門牌號",
                    "經度",
                    "緯度",
                ]

                if include_route_order:
                    fieldnames.append("訪問順序")

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for group in groups:
                    # 建立路線順序對應
                    route_order_map = {}
                    if group.route_order:
                        for order, addr_id in enumerate(group.route_order, 1):
                            route_order_map[addr_id] = order

                    for addr in group.addresses:
                        row = {
                            "分組編號": group.group_id,
                            "地址ID": addr.id,
                            "完整地址": addr.full_address,
                            "區域": addr.district,
                            "村里": addr.village,
                            "鄰別": addr.neighborhood,
                            "街道": addr.street or "",
                            "區段": addr.area or "",
                            "巷": addr.lane or "",
                            "弄": addr.alley or "",
                            "門牌號": addr.number or "",
                            "經度": addr.x_coord,
                            "緯度": addr.y_coord,
                        }

                        if include_route_order:
                            row["訪問順序"] = route_order_map.get(addr.id, "")

                        writer.writerow(row)

            return True

        except Exception as e:
            print(f"CSV 匯出失敗: {e}")
            return False

    @staticmethod
    def export_grouping_result(result: GroupingResult, output_path: str) -> bool:
        """匯出完整分組結果到 CSV

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "分組編號",
                    "分組大小",
                    "目標大小",
                    "預估距離(公尺)",
                    "預估時間(分鐘)",
                    "地址ID",
                    "完整地址",
                    "區域",
                    "村里",
                    "鄰別",
                    "經度",
                    "緯度",
                    "訪問順序",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for group in result.groups:
                    # 建立路線順序對應
                    route_order_map = {}
                    if group.route_order:
                        for order, addr_id in enumerate(group.route_order, 1):
                            route_order_map[addr_id] = order

                    for addr in group.addresses:
                        row = {
                            "分組編號": group.group_id,
                            "分組大小": group.size,
                            "目標大小": result.target_size,
                            "預估距離(公尺)": group.estimated_distance or "",
                            "預估時間(分鐘)": group.estimated_time or "",
                            "地址ID": addr.id,
                            "完整地址": addr.full_address,
                            "區域": addr.district,
                            "村里": addr.village,
                            "鄰別": addr.neighborhood,
                            "經度": addr.x_coord,
                            "緯度": addr.y_coord,
                            "訪問順序": route_order_map.get(addr.id, ""),
                        }

                        writer.writerow(row)

            return True

        except Exception as e:
            print(f"分組結果 CSV 匯出失敗: {e}")
            return False

    @staticmethod
    def export_summary(result: GroupingResult, output_path: str) -> bool:
        """匯出分組摘要到 CSV

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "分組編號",
                    "分組大小",
                    "預估距離(公尺)",
                    "預估時間(分鐘)",
                    "中心經度",
                    "中心緯度",
                    "鄰別分布",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for group in result.groups:
                    center = group.center_coordinates
                    neighborhood_dist = group.address_count_by_neighborhood

                    row = {
                        "分組編號": group.group_id,
                        "分組大小": group.size,
                        "預估距離(公尺)": group.estimated_distance or "",
                        "預估時間(分鐘)": group.estimated_time or "",
                        "中心經度": center[0] if center else "",
                        "中心緯度": center[1] if center else "",
                        "鄰別分布": "; ".join(
                            f"{k}鄰:{v}個" for k, v in neighborhood_dist.items()
                        ),
                    }

                    writer.writerow(row)

            return True

        except Exception as e:
            print(f"摘要 CSV 匯出失敗: {e}")
            return False

    @staticmethod
    def export_addresses_only(groups: List[RouteGroup], output_path: str) -> bool:
        """僅匯出地址資訊到 CSV

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "地址ID",
                    "完整地址",
                    "區域",
                    "村里",
                    "鄰別",
                    "經度",
                    "緯度",
                    "分組編號",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for group in groups:
                    for addr in group.addresses:
                        row = {
                            "地址ID": addr.id,
                            "完整地址": addr.full_address,
                            "區域": addr.district,
                            "村里": addr.village,
                            "鄰別": addr.neighborhood,
                            "經度": addr.x_coord,
                            "緯度": addr.y_coord,
                            "分組編號": group.group_id,
                        }

                        writer.writerow(row)

            return True

        except Exception as e:
            print(f"地址 CSV 匯出失敗: {e}")
            return False

    @staticmethod
    def create_route_sheets(result: GroupingResult, output_dir: str) -> List[str]:
        """為每個分組建立獨立的路線 CSV 檔案

        Args:
            result: 分組結果
            output_dir: 輸出目錄

        Returns:
            建立的檔案路徑列表
        """
        created_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for group in result.groups:
            filename = f"{group.group_id}_路線.csv"
            file_path = output_path / filename

            try:
                with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                    fieldnames = [
                        "訪問順序",
                        "地址ID",
                        "完整地址",
                        "鄰別",
                        "經度",
                        "緯度",
                        "備註",
                    ]

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    # 按路線順序排序
                    if group.route_order:
                        addr_dict = {addr.id: addr for addr in group.addresses}
                        ordered_addresses = [
                            addr_dict[addr_id]
                            for addr_id in group.route_order
                            if addr_id in addr_dict
                        ]
                    else:
                        ordered_addresses = group.addresses

                    for order, addr in enumerate(ordered_addresses, 1):
                        row = {
                            "訪問順序": order,
                            "地址ID": addr.id,
                            "完整地址": addr.full_address,
                            "鄰別": addr.neighborhood,
                            "經度": addr.x_coord,
                            "緯度": addr.y_coord,
                            "備註": "",
                        }

                        writer.writerow(row)

                created_files.append(str(file_path))

            except Exception as e:
                print(f"建立路線檔案 {filename} 失敗: {e}")

        return created_files
