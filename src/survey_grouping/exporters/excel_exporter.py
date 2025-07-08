"""Excel 匯出器

提供將分組結果匯出為 Excel 格式的功能。
"""

from pathlib import Path
from typing import List
import pandas as pd
from survey_grouping.models.group import RouteGroup, GroupingResult


class ExcelExporter:
    """Excel 匯出器"""

    @staticmethod
    def export_groups(groups: List[RouteGroup], output_path: str) -> bool:
        """匯出分組到 Excel 檔案

        Args:
            groups: 分組列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 準備資料
            data = []
            for group in groups:
                # 建立路線順序對應
                route_order_map = {}
                if group.route_order:
                    for order, addr_id in enumerate(group.route_order, 1):
                        route_order_map[addr_id] = order

                for addr in group.addresses:
                    data.append(
                        {
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
                            "訪問順序": route_order_map.get(addr.id, ""),
                            "分組大小": group.size,
                            "預估距離(公尺)": group.estimated_distance or "",
                            "預估時間(分鐘)": group.estimated_time or "",
                        }
                    )

            df = pd.DataFrame(data)
            df.to_excel(output_file, index=False, engine="openpyxl")

            return True

        except Exception as e:
            print(f"Excel 匯出失敗: {e}")
            return False

    @staticmethod
    def export_grouping_result_multi_sheet(
        result: GroupingResult, output_path: str
    ) -> bool:
        """匯出完整分組結果到多工作表 Excel

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 工作表1: 摘要資訊
                summary_data = []
                for group in result.groups:
                    center = group.center_coordinates
                    neighborhood_dist = group.address_count_by_neighborhood

                    summary_data.append(
                        {
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
                    )

                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name="分組摘要", index=False)

                # 工作表2: 詳細地址資料
                detail_data = []
                for group in result.groups:
                    route_order_map = {}
                    if group.route_order:
                        for order, addr_id in enumerate(group.route_order, 1):
                            route_order_map[addr_id] = order

                    for addr in group.addresses:
                        detail_data.append(
                            {
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
                                "訪問順序": route_order_map.get(addr.id, ""),
                            }
                        )

                detail_df = pd.DataFrame(detail_data)
                detail_df.to_excel(writer, sheet_name="詳細地址", index=False)

                # 工作表3: 統計資訊
                result.calculate_statistics()
                stats_data = [
                    ["基本資訊", ""],
                    ["區域", result.district],
                    ["村里", result.village],
                    ["目標分組大小", result.target_size],
                    ["總地址數", result.total_addresses],
                    ["總分組數", result.total_groups],
                    ["建立時間", result.created_at.strftime("%Y-%m-%d %H:%M:%S")],
                    ["", ""],
                    ["分組統計", ""],
                    ["平均分組大小", result.avg_group_size],
                    ["最小分組大小", result.min_group_size],
                    ["最大分組大小", result.max_group_size],
                    ["", ""],
                    ["距離統計", ""],
                    ["總預估距離(公尺)", result.total_estimated_distance or ""],
                    ["總預估時間(分鐘)", result.total_estimated_time or ""],
                ]

                stats_df = pd.DataFrame(stats_data, columns=["項目", "數值"])
                stats_df.to_excel(writer, sheet_name="統計資訊", index=False)

            return True

        except Exception as e:
            print(f"多工作表 Excel 匯出失敗: {e}")
            return False

    @staticmethod
    def create_route_workbook(result: GroupingResult, output_path: str) -> bool:
        """建立路線工作簿（每個分組一個工作表）

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 總覽工作表
                overview_data = []
                for group in result.groups:
                    overview_data.append(
                        {
                            "分組編號": group.group_id,
                            "分組大小": group.size,
                            "預估距離(公尺)": group.estimated_distance or "",
                            "預估時間(分鐘)": group.estimated_time or "",
                            "工作表名稱": f"路線_{group.group_id}",
                        }
                    )

                overview_df = pd.DataFrame(overview_data)
                overview_df.to_excel(writer, sheet_name="總覽", index=False)

                # 為每個分組建立工作表
                for group in result.groups:
                    sheet_name = f"路線_{group.group_id}"

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

                    route_data = []
                    for order, addr in enumerate(ordered_addresses, 1):
                        route_data.append(
                            {
                                "訪問順序": order,
                                "地址ID": addr.id,
                                "完整地址": addr.full_address,
                                "鄰別": addr.neighborhood,
                                "經度": addr.x_coord,
                                "緯度": addr.y_coord,
                                "備註": "",
                            }
                        )

                    route_df = pd.DataFrame(route_data)
                    route_df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True

        except Exception as e:
            print(f"路線工作簿建立失敗: {e}")
            return False

    @staticmethod
    def export_comparison_analysis(
        results: List[GroupingResult], output_path: str
    ) -> bool:
        """匯出多個分組結果的比較分析

        Args:
            results: 分組結果列表
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 比較摘要
                comparison_data = []
                for i, result in enumerate(results, 1):
                    result.calculate_statistics()
                    comparison_data.append(
                        {
                            "方案編號": f"方案{i}",
                            "區域": result.district,
                            "村里": result.village,
                            "目標大小": result.target_size,
                            "總地址數": result.total_addresses,
                            "總分組數": result.total_groups,
                            "平均分組大小": result.avg_group_size,
                            "最小分組": result.min_group_size,
                            "最大分組": result.max_group_size,
                            "總距離(公尺)": result.total_estimated_distance or "",
                            "總時間(分鐘)": result.total_estimated_time or "",
                            "建立時間": result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )

                comparison_df = pd.DataFrame(comparison_data)
                comparison_df.to_excel(writer, sheet_name="方案比較", index=False)

                # 詳細分析
                for i, result in enumerate(results, 1):
                    sheet_name = f"方案{i}_詳細"

                    detail_data = []
                    for group in result.groups:
                        detail_data.append(
                            {
                                "分組編號": group.group_id,
                                "分組大小": group.size,
                                "預估距離": group.estimated_distance or "",
                                "預估時間": group.estimated_time or "",
                                "地址數量": len(group.addresses),
                            }
                        )

                    detail_df = pd.DataFrame(detail_data)
                    detail_df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True

        except Exception as e:
            print(f"比較分析匯出失敗: {e}")
            return False

    @staticmethod
    def export_quality_report(result: GroupingResult, output_path: str) -> bool:
        """匯出品質報告

        Args:
            result: 分組結果
            output_path: 輸出檔案路徑

        Returns:
            是否成功匯出
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 品質指標
                result.calculate_statistics()

                quality_data = []
                for group in result.groups:
                    center = group.center_coordinates
                    coverage = group.coverage_area

                    # 計算品質指標
                    size_deviation = abs(group.size - result.target_size)
                    size_score = max(
                        0, 100 - (size_deviation / result.target_size * 100)
                    )

                    # 地理緊密度評分
                    if coverage and len(coverage) == 4:
                        lat_range = coverage[2] - coverage[0]  # max_lat - min_lat
                        lng_range = coverage[3] - coverage[1]  # max_lng - min_lng
                        compactness_score = max(
                            0, 100 - (lat_range + lng_range) * 10000
                        )
                    else:
                        compactness_score = 0

                    quality_data.append(
                        {
                            "分組編號": group.group_id,
                            "分組大小": group.size,
                            "目標大小": result.target_size,
                            "大小偏差": size_deviation,
                            "大小評分": round(size_score, 2),
                            "緊密度評分": round(compactness_score, 2),
                            "綜合評分": round((size_score + compactness_score) / 2, 2),
                            "預估距離": group.estimated_distance or "",
                            "預估時間": group.estimated_time or "",
                            "中心座標": (
                                f"{center[0]:.6f}, {center[1]:.6f}" if center else ""
                            ),
                        }
                    )

                quality_df = pd.DataFrame(quality_data)
                quality_df.to_excel(writer, sheet_name="品質評估", index=False)

                # 問題分析
                problems = []
                for group in result.groups:
                    group_problems = []

                    # 檢查大小問題
                    if group.size < result.target_size * 0.7:
                        group_problems.append("分組過小")
                    elif group.size > result.target_size * 1.3:
                        group_problems.append("分組過大")

                    # 檢查地理分散問題
                    if group.estimated_distance and group.estimated_distance > 2000:
                        group_problems.append("地理範圍過大")

                    # 檢查鄰別分布
                    neighborhood_dist = group.address_count_by_neighborhood
                    if len(neighborhood_dist) > 5:
                        group_problems.append("跨越鄰別過多")

                    if group_problems:
                        problems.append(
                            {
                                "分組編號": group.group_id,
                                "問題類型": "; ".join(group_problems),
                                "建議": "考慮重新分組或調整參數",
                            }
                        )

                if problems:
                    problems_df = pd.DataFrame(problems)
                    problems_df.to_excel(writer, sheet_name="問題分析", index=False)

            return True

        except Exception as e:
            print(f"品質報告匯出失敗: {e}")
            return False
