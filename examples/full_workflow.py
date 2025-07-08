#!/usr/bin/env python3
"""完整工作流程範例

展示從資料驗證到最終匯出的完整普查路線分組流程。
"""

import os
from datetime import datetime
from pathlib import Path
from survey_grouping.models.address import Address
from survey_grouping.models.group import GroupingResult
from survey_grouping.algorithms.grouping_engine import GroupingEngine
from survey_grouping.algorithms.route_optimizer import RouteOptimizer
from survey_grouping.utils.validators import (
    AddressValidator,
    GroupingValidator,
    DataQualityValidator,
    validate_input_parameters,
)
from survey_grouping.exporters.csv_exporter import CSVExporter
from survey_grouping.exporters.json_exporter import JSONExporter
from survey_grouping.exporters.excel_exporter import ExcelExporter


def create_extended_sample_data():
    """建立擴展的範例資料"""
    addresses = []

    # 安慶里 1-5 鄰的地址
    neighborhoods = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5]
    streets = ["安中路", "安中路", "安和路", "安中路", "安和路", "安平路"]

    for i in range(15):
        neighborhood = neighborhoods[i]
        street = streets[i % len(streets)]
        number = f"{(i + 1) * 10}號"

        # 模擬地理分布
        base_x = 120.2400 + (neighborhood - 1) * 0.002
        base_y = 23.0450 + (neighborhood - 1) * 0.001
        x_coord = base_x + (i % 3) * 0.0005
        y_coord = base_y + (i % 3) * 0.0003

        address = Address(
            id=i + 1,
            district="安南區",
            village="安慶里",
            neighborhood=neighborhood,
            street=street,
            area="一段" if i % 2 == 0 else "二段",
            number=number,
            x_coord=x_coord,
            y_coord=y_coord,
            full_address=f"台南市安南區安慶里{neighborhood}鄰{street}一段{number}",
        )
        addresses.append(address)

    return addresses


def validate_data(addresses, district, village, target_size):
    """資料驗證步驟"""
    print("=== 步驟 1: 資料驗證 ===")

    # 1. 驗證輸入參數
    print("1.1 驗證輸入參數...")
    is_valid, errors = validate_input_parameters(district, village, target_size)
    if not is_valid:
        print("   ✗ 輸入參數驗證失敗:")
        for error in errors:
            print(f"     - {error}")
        return False
    print("   ✓ 輸入參數驗證通過")

    # 2. 驗證地址資料
    print("1.2 驗證地址資料...")
    validation_result = AddressValidator.validate_address_list(addresses)
    print(f"   - 總地址數: {validation_result['total']}")
    print(f"   - 有效地址: {validation_result['valid']}")
    print(f"   - 無效地址: {validation_result['invalid']}")
    print(f"   - 有效率: {validation_result['validity_rate']:.1f}%")

    if validation_result["invalid"] > 0:
        print("   警告: 發現無效地址")
        for error in validation_result["errors"][:3]:  # 只顯示前3個錯誤
            print(f"     - {error}")

    # 3. 資料品質檢查
    print("1.3 資料品質檢查...")
    quality_result = DataQualityValidator.check_data_completeness(addresses)
    print(f"   - 整體品質評分: {quality_result['overall_quality_score']:.1f}")
    print(
        f"   - 座標完整度: {quality_result['completeness_percentages']['has_coordinates']:.1f}%"
    )
    print(
        f"   - 地址完整度: {quality_result['completeness_percentages']['has_full_address']:.1f}%"
    )

    # 4. 重複檢測
    print("1.4 重複檢測...")
    duplicate_result = DataQualityValidator.detect_duplicates(addresses)
    if duplicate_result["total_duplicate_groups"] > 0:
        print(f"   警告: 發現 {duplicate_result['total_duplicate_groups']} 組重複資料")
    else:
        print("   ✓ 未發現重複資料")

    print("   ✓ 資料驗證完成\n")
    return True


def perform_grouping(addresses, target_size):
    """執行分組步驟"""
    print("=== 步驟 2: 地址分組 ===")

    print("2.1 初始化分組引擎...")
    engine = GroupingEngine(target_size=target_size)
    print(f"   - 目標分組大小: {target_size}")

    print("2.2 執行地址分組...")
    groups = engine.group_addresses(addresses)
    print(f"   ✓ 分組完成，共產生 {len(groups)} 個分組")

    # 驗證分組品質
    print("2.3 驗證分組品質...")
    for i, group in enumerate(groups, 1):
        is_valid, message = GroupingValidator.validate_group_size(
            group.addresses, target_size, tolerance=0.4
        )
        status = "✓" if is_valid else "⚠"
        print(f"   {status} 第 {i} 組: {message}")

        # 檢查地理緊密度
        is_compact, compact_msg = GroupingValidator.validate_geographic_compactness(
            group.addresses, max_diameter=1500.0
        )
        compact_status = "✓" if is_compact else "⚠"
        print(f"     {compact_status} 緊密度: {compact_msg}")

    print("   ✓ 分組驗證完成\n")
    return groups


def optimize_routes(groups):
    """路線優化步驟"""
    print("=== 步驟 3: 路線優化 ===")

    print("3.1 比較優化演算法...")
    optimizer = RouteOptimizer()

    # 對第一組進行演算法比較
    if groups:
        comparison = optimizer.compare_algorithms(groups[0].addresses)
        print("   演算法效能比較 (第1組):")
        for algorithm, result in comparison.items():
            distance = result["metrics"]["total_distance"]
            time = result["metrics"]["estimated_time"]
            print(f"     - {algorithm}: {distance:.1f}m, {time}分鐘")

    print("3.2 執行路線優化...")
    optimizer = RouteOptimizer(algorithm="two_opt")  # 使用較好的演算法

    for i, group in enumerate(groups, 1):
        print(f"   優化第 {i} 組路線...")

        # 優化路線
        route_order = optimizer.optimize_route(group.addresses)
        group.route_order = route_order

        # 計算指標
        metrics = optimizer.calculate_route_metrics(group.addresses, route_order)
        group.estimated_distance = metrics["total_distance"]
        group.estimated_time = metrics["estimated_time"]

        print(f"     - 最終距離: {group.estimated_distance:.1f} 公尺")
        print(f"     - 預估時間: {group.estimated_time} 分鐘")

    print("   ✓ 路線優化完成\n")
    return groups


def create_grouping_result(groups, district, village, target_size, total_addresses):
    """建立分組結果"""
    print("=== 步驟 4: 建立分組結果 ===")

    result = GroupingResult(
        district=district,
        village=village,
        target_size=target_size,
        total_addresses=total_addresses,
        total_groups=len(groups),
        groups=groups,
        created_at=datetime.now(),
    )

    # 計算統計資訊
    result.calculate_statistics()

    print("4.1 分組統計:")
    print(f"   - 總地址數: {result.total_addresses}")
    print(f"   - 總分組數: {result.total_groups}")
    print(f"   - 平均分組大小: {result.avg_group_size:.1f}")
    print(f"   - 分組大小範圍: {result.min_group_size} - {result.max_group_size}")

    if result.total_estimated_distance:
        print(f"   - 總預估距離: {result.total_estimated_distance:.1f} 公尺")
        print(
            f"   - 平均每組距離: {result.total_estimated_distance/len(groups):.1f} 公尺"
        )

    if result.total_estimated_time:
        print(f"   - 總預估時間: {result.total_estimated_time} 分鐘")
        print(f"   - 平均每組時間: {result.total_estimated_time/len(groups):.1f} 分鐘")

    print("   ✓ 分組結果建立完成\n")
    return result


def export_results(result):
    """匯出結果步驟"""
    print("=== 步驟 5: 匯出結果 ===")

    # 建立輸出目錄
    output_dir = Path("output/full_workflow")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{result.district}_{result.village}_{timestamp}"

    print("5.1 匯出 CSV 格式...")

    # 詳細結果
    csv_path = output_dir / f"{base_name}_詳細.csv"
    if CSVExporter.export_grouping_result(result, str(csv_path)):
        print(f"   ✓ 詳細結果: {csv_path}")

    # 摘要
    summary_path = output_dir / f"{base_name}_摘要.csv"
    if CSVExporter.export_summary(result, str(summary_path)):
        print(f"   ✓ 摘要: {summary_path}")

    # 個別路線檔案
    route_files = CSVExporter.create_route_sheets(result, str(output_dir / "routes"))
    if route_files:
        print(f"   ✓ 個別路線檔案: {len(route_files)} 個")

    print("5.2 匯出 JSON 格式...")

    # 完整 JSON
    json_path = output_dir / f"{base_name}_完整.json"
    if JSONExporter.export_grouping_result(result, str(json_path)):
        print(f"   ✓ 完整結果: {json_path}")

    # GeoJSON (地圖用)
    geojson_path = output_dir / f"{base_name}_地圖.geojson"
    if JSONExporter.export_geojson(result.groups, str(geojson_path)):
        print(f"   ✓ 地圖資料: {geojson_path}")

    # 統計摘要
    stats_path = output_dir / f"{base_name}_統計.json"
    if JSONExporter.export_statistics_summary(result, str(stats_path)):
        print(f"   ✓ 統計摘要: {stats_path}")

    print("5.3 匯出 Excel 格式...")

    # 多工作表 Excel
    excel_path = output_dir / f"{base_name}_完整.xlsx"
    if ExcelExporter.export_grouping_result_multi_sheet(result, str(excel_path)):
        print(f"   ✓ 多工作表: {excel_path}")

    # 路線工作簿
    routes_excel_path = output_dir / f"{base_name}_路線.xlsx"
    if ExcelExporter.create_route_workbook(result, str(routes_excel_path)):
        print(f"   ✓ 路線工作簿: {routes_excel_path}")

    # 品質報告
    quality_path = output_dir / f"{base_name}_品質報告.xlsx"
    if ExcelExporter.export_quality_report(result, str(quality_path)):
        print(f"   ✓ 品質報告: {quality_path}")

    print("   ✓ 所有格式匯出完成\n")
    return output_dir


def main():
    """主要執行函數"""
    print("=== 台南市志工普查路線分組系統 - 完整工作流程 ===\n")

    # 設定參數
    district = "安南區"
    village = "安慶里"
    target_size = 5  # 每組目標 5 個地址

    print(f"處理區域: {district} {village}")
    print(f"目標分組大小: {target_size}\n")

    try:
        # 1. 建立範例資料
        addresses = create_extended_sample_data()
        print(f"載入了 {len(addresses)} 個地址\n")

        # 2. 資料驗證
        if not validate_data(addresses, district, village, target_size):
            print("資料驗證失敗，流程終止")
            return

        # 3. 執行分組
        groups = perform_grouping(addresses, target_size)

        # 4. 路線優化
        groups = optimize_routes(groups)

        # 5. 建立結果
        result = create_grouping_result(
            groups, district, village, target_size, len(addresses)
        )

        # 6. 匯出結果
        output_dir = export_results(result)

        # 7. 完成摘要
        print("=== 流程完成摘要 ===")
        print(f"✓ 處理地址: {len(addresses)} 個")
        print(f"✓ 產生分組: {len(groups)} 個")
        print(f"✓ 平均分組大小: {result.avg_group_size:.1f}")
        print(f"✓ 輸出目錄: {output_dir}")
        print(f"✓ 處理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n=== 完整工作流程執行完成 ===")

    except Exception as e:
        print(f"執行過程中發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
