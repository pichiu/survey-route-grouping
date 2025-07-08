"""JSON 匯出器

提供將分組結果匯出為 JSON 格式的功能。
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from survey_grouping.models.group import RouteGroup, GroupingResult


class JSONExporter:
    """JSON 匯出器"""

    @staticmethod
    def export_groups(groups: List[RouteGroup], output_path: str) -> bool:
        """匯出分組到 JSON 檔案

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            groups_data = []
            for group in groups:
                group_data = {
                    "group_id": group.group_id,
                    "size": group.size,
                    "estimated_distance": group.estimated_distance,
                    "estimated_time": group.estimated_time,
                    "route_order": group.route_order,
                    "center_coordinates": group.center_coordinates,
                    "coverage_area": group.coverage_area,
                    "addresses": [
                        {
                            "id": addr.id,
                            "full_address": addr.full_address,
                            "district": addr.district,
                            "village": addr.village,
                            "neighborhood": addr.neighborhood,
                            "street": addr.street,
                            "area": addr.area,
                            "lane": addr.lane,
                            "alley": addr.alley,
                            "number": addr.number,
                            "coordinates": {
                                "longitude": addr.x_coord,
                                "latitude": addr.y_coord,
                            },
                        }
                        for addr in group.addresses
                    ],
                }
                groups_data.append(group_data)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    groups_data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=JSONExporter._json_serializer,
                )

            return True

        except Exception as e:
            print(f"JSON 匯出失敗: {e}")
            return False

    @staticmethod
    def export_grouping_result(result: GroupingResult, output_path: str) -> bool:
        """匯出完整分組結果到 JSON

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 計算統計資訊
            result.calculate_statistics()

            result_data = {
                "metadata": {
                    "district": result.district,
                    "village": result.village,
                    "target_size": result.target_size,
                    "total_addresses": result.total_addresses,
                    "total_groups": result.total_groups,
                    "created_at": result.created_at.isoformat(),
                    "statistics": {
                        "avg_group_size": result.avg_group_size,
                        "min_group_size": result.min_group_size,
                        "max_group_size": result.max_group_size,
                        "total_estimated_distance": result.total_estimated_distance,
                        "total_estimated_time": result.total_estimated_time,
                    },
                },
                "groups": [
                    {
                        "group_id": group.group_id,
                        "size": group.size,
                        "estimated_distance": group.estimated_distance,
                        "estimated_time": group.estimated_time,
                        "route_order": group.route_order,
                        "center_coordinates": group.center_coordinates,
                        "coverage_area": group.coverage_area,
                        "neighborhood_distribution": group.address_count_by_neighborhood,
                        "addresses": [
                            {
                                "id": addr.id,
                                "full_address": addr.full_address,
                                "district": addr.district,
                                "village": addr.village,
                                "neighborhood": addr.neighborhood,
                                "street": addr.street,
                                "area": addr.area,
                                "lane": addr.lane,
                                "alley": addr.alley,
                                "number": addr.number,
                                "coordinates": {
                                    "longitude": addr.x_coord,
                                    "latitude": addr.y_coord,
                                },
                                "address_type": addr.address_type,
                            }
                            for addr in group.addresses
                        ],
                    }
                    for group in result.groups
                ],
                "coverage_summary": result.coverage_summary,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    result_data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=JSONExporter._json_serializer,
                )

            return True

        except Exception as e:
            print(f"分組結果 JSON 匯出失敗: {e}")
            return False

    @staticmethod
    def export_geojson(groups: List[RouteGroup], output_path: str) -> bool:
        """匯出為 GeoJSON 格式（用於地圖顯示）

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            features = []

            for group in groups:
                for addr in group.addresses:
                    if addr.has_valid_coordinates:
                        feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [addr.x_coord, addr.y_coord],
                            },
                            "properties": {
                                "id": addr.id,
                                "full_address": addr.full_address,
                                "district": addr.district,
                                "village": addr.village,
                                "neighborhood": addr.neighborhood,
                                "group_id": group.group_id,
                                "group_size": group.size,
                                "address_type": addr.address_type,
                            },
                        }
                        features.append(feature)

            geojson_data = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "total_groups": len(groups),
                    "total_addresses": sum(len(group.addresses) for group in groups),
                    "created_at": datetime.now().isoformat(),
                },
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    geojson_data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=JSONExporter._json_serializer,
                )

            return True

        except Exception as e:
            print(f"GeoJSON 匯出失敗: {e}")
            return False

    @staticmethod
    def export_route_optimization_data(
        groups: List[RouteGroup], output_path: str
    ) -> bool:
        """匯出路線優化資料

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            route_data = []

            for group in groups:
                if not group.addresses:
                    continue

                # 建立距離矩陣
                addresses = group.addresses
                distance_matrix = []

                for i, addr1 in enumerate(addresses):
                    row = []
                    for j, addr2 in enumerate(addresses):
                        if i == j:
                            row.append(0.0)
                        else:
                            distance = addr1.distance_to(addr2) or 0.0
                            row.append(round(distance, 2))
                    distance_matrix.append(row)

                group_route_data = {
                    "group_id": group.group_id,
                    "addresses": [
                        {
                            "id": addr.id,
                            "index": i,
                            "full_address": addr.full_address,
                            "coordinates": [addr.x_coord, addr.y_coord],
                        }
                        for i, addr in enumerate(addresses)
                    ],
                    "distance_matrix": distance_matrix,
                    "optimized_route": group.route_order,
                    "total_distance": group.calculate_route_distance(),
                    "estimated_time": group.estimated_time,
                }

                route_data.append(group_route_data)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    route_data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=JSONExporter._json_serializer,
                )

            return True

        except Exception as e:
            print(f"路線優化資料匯出失敗: {e}")
            return False

    @staticmethod
    def export_statistics_summary(result: GroupingResult, output_path: str) -> bool:
        """匯出統計摘要

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 計算詳細統計
            result.calculate_statistics()

            group_sizes = [group.size for group in result.groups]
            distances = [
                group.estimated_distance
                for group in result.groups
                if group.estimated_distance
            ]
            times = [
                group.estimated_time for group in result.groups if group.estimated_time
            ]

            statistics = {
                "basic_info": {
                    "district": result.district,
                    "village": result.village,
                    "target_size": result.target_size,
                    "total_addresses": result.total_addresses,
                    "total_groups": result.total_groups,
                    "created_at": result.created_at.isoformat(),
                },
                "group_size_analysis": {
                    "average": result.avg_group_size,
                    "minimum": result.min_group_size,
                    "maximum": result.max_group_size,
                    "distribution": {
                        str(size): group_sizes.count(size) for size in set(group_sizes)
                    },
                },
                "distance_analysis": {
                    "total_distance": result.total_estimated_distance,
                    "average_per_group": (
                        sum(distances) / len(distances) if distances else 0
                    ),
                    "min_distance": min(distances) if distances else 0,
                    "max_distance": max(distances) if distances else 0,
                },
                "time_analysis": {
                    "total_time": result.total_estimated_time,
                    "average_per_group": sum(times) / len(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0,
                },
                "coverage_analysis": result.coverage_summary,
                "efficiency_metrics": {
                    "addresses_per_group_variance": (
                        sum((size - result.avg_group_size) ** 2 for size in group_sizes)
                        / len(group_sizes)
                        if group_sizes
                        else 0
                    ),
                    "target_achievement_rate": (
                        sum(
                            1
                            for size in group_sizes
                            if abs(size - result.target_size) <= 3
                        )
                        / len(group_sizes)
                        * 100
                        if group_sizes
                        else 0
                    ),
                },
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    statistics,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=JSONExporter._json_serializer,
                )

            return True

        except Exception as e:
            print(f"統計摘要匯出失敗: {e}")
            return False

    @staticmethod
    def _json_serializer(obj):
        """JSON 序列化輔助函數"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)
